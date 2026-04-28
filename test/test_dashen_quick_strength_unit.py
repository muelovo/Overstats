from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
PARENT_DIR = REPO_ROOT.parent
for candidate in (PARENT_DIR, REPO_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from overstats.src.modules.errors import ModuleError
    from overstats.src.modules.dashen_quick_strength.engine import (
        _build_player_competitive_meta,
        calculate_pre_match_streak,
        convert_rank_score,
        normalize_limit,
        score_to_rank,
    )
    from overstats.src.modules.dashen_quick_strength.render import render_quick_strength
    from overstats.src.modules.dashen_quick_strength.requests import DashenQuickStrengthQuery, DashenQuickStrengthRequests
    from overstats.src.modules.dashen_quick_strength.service import DashenQuickStrengthModule
except ModuleNotFoundError:
    from src.modules.errors import ModuleError
    from src.modules.dashen_quick_strength.engine import (
        _build_player_competitive_meta,
        calculate_pre_match_streak,
        convert_rank_score,
        normalize_limit,
        score_to_rank,
    )
    from src.modules.dashen_quick_strength.render import render_quick_strength
    from src.modules.dashen_quick_strength.requests import DashenQuickStrengthQuery, DashenQuickStrengthRequests
    from src.modules.dashen_quick_strength.service import DashenQuickStrengthModule


class EngineFunctionTests(unittest.TestCase):
    def test_normalize_limit_clamps(self) -> None:
        self.assertEqual(normalize_limit(None), 12)
        self.assertEqual(normalize_limit(2), 3)
        self.assertEqual(normalize_limit(50), 12)

    def test_convert_rank_score(self) -> None:
        self.assertEqual(convert_rank_score(395), 2500)
        self.assertEqual(convert_rank_score(255), 2000)
        self.assertEqual(convert_rank_score(459), 3400)
        self.assertIsNone(convert_rank_score(0))

    def test_score_to_rank(self) -> None:
        self.assertEqual(score_to_rank(1000), "Bronze 5")
        self.assertEqual(score_to_rank(2875), "Platinum 2")
        self.assertEqual(score_to_rank(0), "Unranked")

    def test_calculate_pre_match_streak(self) -> None:
        history = [
            {"matchId": "target", "matchRet": 1},
            {"matchId": "older-1", "matchRet": 1},
            {"matchId": "older-2", "matchRet": 1},
            {"matchId": "older-3", "matchRet": -1},
        ]
        self.assertEqual(calculate_pre_match_streak(history, "target"), 2)

        history = [
            {"matchId": "target", "matchRet": -1},
            {"matchId": "older-1", "matchRet": -1},
            {"matchId": "older-2", "matchRet": -1},
            {"matchId": "older-3", "matchRet": 1},
        ]
        self.assertEqual(calculate_pre_match_streak(history, "target"), -2)

    def test_build_player_competitive_meta_uses_previous_season_fallback(self) -> None:
        payloads = [
            (22, []),
            (
                21,
                [
                    {"roleType": "tank", "lastRankInfo": {"rankScore": 355}},
                    {"roleType": "dps", "lastRankInfo": {"rankScore": 295}},
                ],
            ),
        ]
        meta = _build_player_competitive_meta(payloads, live_season=22)
        self.assertEqual(meta["latest_role_scores"]["tank"], convert_rank_score(355))
        self.assertEqual(meta["latest_role_seasons"]["tank"], 21)
        self.assertEqual(meta["current_role_scores"], {})


class QuickStrengthServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_customer_token_direct_query(self) -> None:
        engine = _RecordingEngine(_sample_engine_payload())
        module = DashenQuickStrengthModule(api_client=SimpleNamespace(), search_module=_ExplodingSearchModule())
        module.engine = engine
        module._load_ow_config = lambda: {"heroList": []}

        result = await module.query_quick_strength(
            DashenQuickStrengthQuery(customer_token="token-1", limit=99),
            render=False,
        )

        self.assertEqual(result.customer_token, "token-1")
        self.assertEqual(engine.calls[0]["limit"], 12)
        self.assertEqual(result.summary.match_count, 3)
        self.assertEqual(len(result.matches), 3)

    async def test_bnet_query_resolves_customer_token(self) -> None:
        engine = _RecordingEngine(_sample_engine_payload())
        search_module = _StubSearchModule()
        module = DashenQuickStrengthModule(api_client=SimpleNamespace(), search_module=search_module)
        module.engine = engine
        module._load_ow_config = lambda: {"heroList": []}

        result = await module.query_quick_strength(
            DashenQuickStrengthQuery(bnet_id="Player#12345", limit=5),
            render=False,
        )

        self.assertEqual(search_module.calls, [("Player#12345", False)])
        self.assertEqual(engine.calls[0]["customer_token"], "resolved-token")
        self.assertEqual(engine.calls[0]["limit"], 5)
        self.assertEqual(result.full_id, "Player#12345")

    async def test_empty_match_payload_raises_module_error(self) -> None:
        engine = _RecordingEngine({"summary": {"match_count": 0}, "matches": []})
        module = DashenQuickStrengthModule(api_client=SimpleNamespace(), search_module=_ExplodingSearchModule())
        module.engine = engine
        module._load_ow_config = lambda: {"heroList": []}

        with self.assertRaises(ModuleError) as ctx:
            await module.query_quick_strength(
                DashenQuickStrengthQuery(customer_token="token-1"),
                render=False,
            )
        self.assertEqual(ctx.exception.error, "quick_strength_empty")


class QuickStrengthRequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_quick_history_stops_when_target_found(self) -> None:
        api_client = _StubQuickHistoryClient(
            {
                1: {"code": 0, "data": {"matchList": [{"matchId": "target", "matchRet": 1}]}},
                2: {"code": 0, "data": {"matchList": [{"matchId": "older", "matchRet": -1}]}},
            }
        )
        requests = DashenQuickStrengthRequests(api_client=api_client)

        result = await requests.list_quick_history_pages(
            "token-1",
            logical_season=22,
            target_match_id="target",
            start_page=1,
            max_pages=5,
        )

        self.assertEqual(api_client.pages, [1])
        self.assertTrue(result["found_target"])
        self.assertEqual(len(result["history"]), 1)


class RenderSmokeTests(unittest.TestCase):
    def test_render_quick_strength_returns_png_bytes(self) -> None:
        try:
            image = render_quick_strength(
                player_name="Player#12345",
                bnet_id="12345",
                summary=_sample_engine_payload()["summary"],
                matches=_sample_engine_payload()["matches"],
                avatar_bytes=None,
            )
        except RuntimeError as exc:
            self.skipTest(str(exc))
            return

        self.assertTrue(image.content.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(image.media_type, "image/png")


class _RecordingEngine:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def build(self, **kwargs):
        self.calls.append(kwargs)
        return self.payload


class _StubSearchModule:
    def __init__(self) -> None:
        self.calls = []

    async def search(self, query, render=False):
        self.calls.append((query, render))
        result = SimpleNamespace(
            query=query,
            customer_token="resolved-token",
            bnet_id="12345",
            full_id="Player#12345",
            icon_url="",
            payload={"code": 0, "data": {}},
        )
        return SimpleNamespace(result=result)


class _ExplodingSearchModule:
    async def search(self, query, render=False):
        raise AssertionError("search() should not be called for direct customer_token queries")


class _StubQuickHistoryClient:
    def __init__(self, page_payloads) -> None:
        self.page_payloads = dict(page_payloads)
        self.pages = []

    async def query_match_list(self, customer_token, game_mode, page=1, season=None):
        self.pages.append(int(page))
        return self.page_payloads.get(int(page), {"code": 0, "data": {"matchList": []}})


def _sample_engine_payload():
    return {
        "summary": {
            "match_count": 3,
            "overall_avg_score": 2875.4,
            "overall_avg_rank": "Platinum 2",
            "score_range": {"min": 2520, "max": 3210},
            "used_previous_season_fallback": False,
        },
        "matches": [
            {
                "match_id": "m1",
                "begin_ts": 1777098388787,
                "result": 1,
                "map_guid": "map-1",
                "avg_score": 2920.0,
                "avg_rank": "Platinum 1",
                "role_range": {"min": 2510, "max": 3350},
                "all_role_range": {"min": 2320, "max": 3470},
                "current_role_range": {"min": 2550, "max": 3220},
                "current_all_role_range": {"min": 2410, "max": 3340},
                "team_scores": [3010, 2890, 2760],
                "enemy_scores": [2940, 2810, 2670],
                "team_streak_avg": 1.2,
                "enemy_streak_avg": -0.4,
            },
            {
                "match_id": "m2",
                "begin_ts": 1777098389799,
                "result": -1,
                "map_guid": "map-2",
                "avg_score": 2810.0,
                "avg_rank": "Platinum 2",
                "role_range": {"min": 2450, "max": 3190},
                "all_role_range": {"min": 2330, "max": 3380},
                "current_role_range": {"min": 2480, "max": 3060},
                "current_all_role_range": {"min": 2400, "max": 3210},
                "team_scores": [2860, 2810, 2740],
                "enemy_scores": [2920, 2790, 2750],
                "team_streak_avg": -1.0,
                "enemy_streak_avg": 0.7,
            },
            {
                "match_id": "m3",
                "begin_ts": 1777098390800,
                "result": 1,
                "map_guid": "map-3",
                "avg_score": 2896.2,
                "avg_rank": "Platinum 2",
                "role_range": {"min": 2580, "max": 3210},
                "all_role_range": {"min": 2390, "max": 3410},
                "current_role_range": {"min": 2620, "max": 3170},
                "current_all_role_range": {"min": 2450, "max": 3260},
                "team_scores": [3000, 2870, 2820],
                "enemy_scores": [2950, 2840, 2660],
                "team_streak_avg": 0.3,
                "enemy_streak_avg": -1.1,
            },
        ],
    }


if __name__ == "__main__":
    unittest.main()
