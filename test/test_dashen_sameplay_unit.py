from __future__ import annotations

import base64
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Any, cast
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
PARENT_DIR = REPO_ROOT.parent
for candidate in (PARENT_DIR, REPO_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    import overstats.src.modules.dashen_sameplay.service as sameplay_service_module
    from overstats.src.modules.errors import ModuleError
except ModuleNotFoundError:
    import src.modules.dashen_sameplay.service as sameplay_service_module
    from src.modules.errors import ModuleError


DashenMatchQuery = sameplay_service_module.DashenMatchQuery
DashenSameplayModule = sameplay_service_module.DashenSameplayModule
DashenSameplayQuery = sameplay_service_module.DashenSameplayQuery


class DashenSameplayModuleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        sameplay_service_module._SAMEPLAY_LIST_CACHE.clear()
        self._originals = {
            "render_match_list": sameplay_service_module.render_match_list,
            "render_match_detail": sameplay_service_module.render_match_detail,
            "decorate_rendered_image_header": sameplay_service_module.decorate_rendered_image_header,
            "render_player_hero_detail": sameplay_service_module.render_player_hero_detail,
            "render_all_players_waterfall": sameplay_service_module.render_all_players_waterfall,
            "render_analysis_report": sameplay_service_module.render_analysis_report,
            "build_target_hero_icons": sameplay_service_module.build_target_hero_icons,
            "map_name_for_match": sameplay_service_module.map_name_for_match,
            "map_icon_image_for_match": sameplay_service_module.map_icon_image_for_match,
        }
        sameplay_service_module.render_match_list = lambda *args, **kwargs: _fake_image("sameplay-list")
        sameplay_service_module.render_match_detail = lambda *args, **kwargs: _fake_image("main")
        sameplay_service_module.decorate_rendered_image_header = lambda image, *args, **kwargs: image
        sameplay_service_module.render_player_hero_detail = lambda player_name, *args, **kwargs: _fake_image(
            f"hero:{player_name}"
        )
        sameplay_service_module.render_all_players_waterfall = lambda *args, **kwargs: _fake_image("waterfall")
        sameplay_service_module.render_analysis_report = lambda *args, **kwargs: _fake_image("analysis")
        sameplay_service_module.build_target_hero_icons = lambda *args, **kwargs: []
        sameplay_service_module.map_name_for_match = lambda *args, **kwargs: "Test Map"
        sameplay_service_module.map_icon_image_for_match = lambda *args, **kwargs: None

    def tearDown(self) -> None:
        sameplay_service_module._SAMEPLAY_LIST_CACHE.clear()
        for name, value in self._originals.items():
            setattr(sameplay_service_module, name, value)

    async def test_common_match_intersection_dedup_sort_and_counts(self) -> None:
        module = _build_sameplay_module()
        requests = cast(_StubSameplayRequests, module.requests)

        result = await module.query_sameplay_list(
            DashenSameplayQuery(
                player1_bnet_id="Alpha#1111",
                player2_bnet_id="Bravo#2222",
                include_previous_season=True,
                limit=1,
            ),
            render=False,
        )

        self.assertEqual(result.player1.customer_token, "token-alpha")
        self.assertEqual(result.player2.customer_token, "token-bravo")
        self.assertEqual([match["matchId"] for match in result.matches], ["m2"])
        self.assertEqual([match["matchId"] for match in result.all_matches], ["m2", "m1"])
        self.assertEqual(result.summary["total_common_count"], 2)
        self.assertEqual(result.summary["returned_count"], 1)
        self.assertEqual(result.summary["quick_count"], 1)
        self.assertEqual(result.summary["competitive_count"], 1)
        self.assertEqual(result.summary["scanned_count"], 4)
        self.assertFalse(result.summary["scan_complete"])
        self.assertEqual(
            requests.fetch_page_calls,
            [
                ("token-alpha", None, "sport", 1),
                ("token-alpha", None, "leisure", 1),
                ("token-bravo", None, "sport", 1),
                ("token-bravo", None, "leisure", 1),
            ],
        )

    async def test_same_player_resolution_is_rejected(self) -> None:
        module = _build_sameplay_module(
            resolved_players={
                "Alpha#1111": {"customer_token": "token-shared", "full_id": "Alpha#1111", "bnet_id": "1111"},
                "Mirror#1111": {"customer_token": "token-shared", "full_id": "Mirror#1111", "bnet_id": "1111"},
            }
        )

        with self.assertRaises(ModuleError) as context:
            await module.query_sameplay_list(
                DashenSameplayQuery(
                    player1_bnet_id="Alpha#1111",
                    player2_bnet_id="Mirror#1111",
                ),
                render=False,
            )

        self.assertEqual(context.exception.error, "sameplay_same_player")

    async def test_list_replies_store_only_visible_matches_in_meta(self) -> None:
        module = _build_sameplay_module()

        result = await module.query_sameplay_list_replies(
            DashenSameplayQuery(
                player1_bnet_id="Alpha#1111",
                player2_bnet_id="Bravo#2222",
                limit=1,
            )
        )

        self.assertEqual(result.summary["returned_count"], 1)
        self.assertEqual(len(result.replies), 2)
        self.assertEqual(result.replies[0]["meta_type"], "ds_sameplay_list")
        self.assertEqual(result.replies[0]["data"]["context_type"], "ds_sameplay_list")
        self.assertEqual(len(result.replies[0]["data"]["match_entries"]), 1)
        self.assertEqual(result.replies[0]["data"]["match_entries"][0]["matchId"], "m2")
        self.assertEqual(result.replies[0]["data"]["customer_tokens"]["player1"], "token-alpha")
        self.assertEqual(result.replies[0]["data"]["customer_tokens"]["player2"], "token-bravo")
        self.assertEqual(_reply_image_bytes(result.replies[1]), b"sameplay-list")

    async def test_detail_replies_follow_expected_image_order(self) -> None:
        module = _build_sameplay_module()
        query = DashenSameplayQuery(player1_bnet_id="Alpha#1111", player2_bnet_id="Bravo#2222", limit=1)

        base_result = await module.query_sameplay_detail_replies(query, index=0, show_all_heroes=False, analyze=False)
        self.assertEqual(
            [_reply_image_bytes(reply) for reply in base_result.replies if reply.get("type") == "image"],
            [b"main", "hero:Alpha#1111".encode("utf-8"), "hero:Bravo#2222".encode("utf-8")],
        )

        waterfall_result = await module.query_sameplay_detail_replies(query, index=0, show_all_heroes=True, analyze=False)
        self.assertEqual(
            [_reply_image_bytes(reply) for reply in waterfall_result.replies if reply.get("type") == "image"],
            [b"main", "hero:Alpha#1111".encode("utf-8"), "hero:Bravo#2222".encode("utf-8"), b"waterfall"],
        )

        analysis_result = await module.query_sameplay_detail_replies(query, index=0, show_all_heroes=True, analyze=True)
        self.assertEqual(
            [_reply_image_bytes(reply) for reply in analysis_result.replies if reply.get("type") == "image"],
            [b"main", "hero:Alpha#1111".encode("utf-8"), "hero:Bravo#2222".encode("utf-8"), b"waterfall", b"analysis"],
        )

    async def test_second_focus_player_failure_degrades_to_text_note(self) -> None:
        module = _build_sameplay_module(failing_focus_tokens={"token-bravo"})

        result = await module.query_sameplay_detail_replies(
            DashenSameplayQuery(player1_bnet_id="Alpha#1111", player2_bnet_id="Bravo#2222", limit=1),
            index=0,
            show_all_heroes=True,
            analyze=True,
        )

        image_bytes = [_reply_image_bytes(reply) for reply in result.replies if reply.get("type") == "image"]
        text_replies = [str(reply.get("data") or "") for reply in result.replies if reply.get("type") == "text"]
        self.assertEqual(image_bytes, [b"main", "hero:Alpha#1111".encode("utf-8"), b"waterfall", b"analysis"])
        self.assertEqual(len(text_replies), 1)
        self.assertIn("Bravo#2222", text_replies[0])
        self.assertIn("Failed to fetch hero detail", text_replies[0])


def _build_sameplay_module(
    *,
    resolved_players: dict[str, dict[str, str]] | None = None,
    failing_focus_tokens: set[str] | None = None,
) -> DashenSameplayModule:
    players = resolved_players or {
        "Alpha#1111": {"customer_token": "token-alpha", "full_id": "Alpha#1111", "bnet_id": "1111"},
        "Bravo#2222": {"customer_token": "token-bravo", "full_id": "Bravo#2222", "bnet_id": "2222"},
    }
    page_map = {
        ("token-alpha", None, "sport", 1): [{"matchId": "m2", "beginTs": 200, "gameMode": "sport"}],
        ("token-alpha", None, "leisure", 1): [{"matchId": "m1", "beginTs": 100, "gameMode": "leisure"}],
        ("token-alpha", None, "sport", 2): [{"matchId": "alpha-only", "beginTs": 50, "gameMode": "sport"}],
        ("token-bravo", None, "sport", 1): [{"matchId": "m2", "beginTs": 200, "gameMode": "sport"}],
        ("token-bravo", None, "leisure", 1): [{"matchId": "m1", "beginTs": 100, "gameMode": "leisure"}],
        ("token-bravo", None, "sport", 2): [{"matchId": "bravo-only", "beginTs": 40, "gameMode": "sport"}],
        ("token-shared", None, "sport", 1): [{"matchId": "m2", "beginTs": 200, "gameMode": "sport"}],
    }
    detail_payloads = {
        ("token-alpha", "m2"): _sample_detail_payload("Alpha#1111", "1111", "Bravo#2222", "2222"),
        ("token-bravo", "m2"): _sample_detail_payload("Bravo#2222", "2222", "Alpha#1111", "1111"),
    }
    requests = _StubSameplayRequests(
        page_map=page_map,
        detail_payloads=detail_payloads,
        failing_focus_tokens=failing_focus_tokens or set(),
    )
    module = DashenSameplayModule(requests=requests)
    module.match_module = _StubMatchModule(players)
    return module


class _StubSameplayRequests:
    def __init__(
        self,
        *,
        page_map: dict[tuple[str, Any, str, int], list[dict[str, object]]],
        detail_payloads: dict[tuple[str, str], dict[str, object]],
        failing_focus_tokens: set[str],
    ) -> None:
        self.page_map = page_map
        self.detail_payloads = detail_payloads
        self.failing_focus_tokens = set(failing_focus_tokens)
        self.fetch_page_calls: list[tuple[str, object, str, int]] = []
        self.detail_calls: list[tuple[str, str]] = []
        self.focus_calls: list[tuple[str, str]] = []
        self.api_client = self

    async def fetch_history_matches_page(
        self,
        customer_token: str,
        *,
        page,
        season,
        game_modes,
        fight_modes,
        **kwargs,
    ) -> list[dict[str, object]]:
        self.assert_no_fight_modes(fight_modes)
        results: list[dict[str, object]] = []
        for game_mode in game_modes:
            self.fetch_page_calls.append((customer_token, season, str(game_mode), int(page)))
            for item in self.page_map.get((customer_token, season, str(game_mode), int(page)), []):
                results.append(dict(item))
        return results

    def assert_no_fight_modes(self, fight_modes) -> None:
        if tuple(fight_modes):
            raise AssertionError(f"sameplay should not request fight modes: {fight_modes}")

    async def get_match_detail(self, customer_token: str, match: dict[str, object]):
        match_id = str(match.get("matchId") or "")
        self.detail_calls.append((customer_token, match_id))
        payload = self.detail_payloads[(customer_token, match_id)]
        return SimpleNamespace(match_id=match_id, match_kind="normal", payload=dict(payload), source_match=dict(match))

    async def query_match_info(self, customer_token: str, match_id: str) -> dict[str, object]:
        self.focus_calls.append((customer_token, match_id))
        if customer_token in self.failing_focus_tokens:
            raise RuntimeError("focus detail unavailable")
        return dict(self.detail_payloads[(customer_token, match_id)])


class _StubMatchModule:
    def __init__(self, resolved_players: dict[str, dict[str, str]]) -> None:
        self.resolved_players = dict(resolved_players)

    async def _resolve_query(self, query):
        if query.customer_token:
            return query, None
        resolved = self.resolved_players[query.bnet_id]
        resolved_query = DashenMatchQuery(
            customer_token=resolved["customer_token"],
            bnet_id=resolved["full_id"],
            seasons=query.seasons,
            include_previous_season=query.include_previous_season,
            include_fight=query.include_fight,
            target_count=query.target_count,
            filters=query.filters,
        )
        resolved_bnet = SimpleNamespace(
            query=query.bnet_id,
            full_id=resolved["full_id"],
            bnet_id=resolved["bnet_id"],
            customer_token=resolved["customer_token"],
        )
        return resolved_query, resolved_bnet

    async def _build_all_player_details(self, detail_root, match_id, *, query_full_id, query_bnet_id):
        return (
            [
                {"name": query_full_id, "heroList": [{"heroName": "Ana"}], "team_type": "teammate"},
                {"name": "Other#3333", "heroList": [{"heroName": "Cassidy"}], "team_type": "enemy"},
            ],
            query_full_id,
        )

    async def _build_ai_analysis(self, *, match_data, all_player_details, target_id):
        return {"json": {"player_id": target_id}, "footer_source": "AI analysis"}

    def _ordered_player_ids(self, detail_root):
        ordered = []
        for team_key in ("teammateList", "enemyList"):
            for player in detail_root.get(team_key, []) or []:
                name = str(player.get("name") or "").strip()
                if name:
                    ordered.append(name)
        return ordered

    def _is_competitive_match(self, detail_root, match_kind, source_match):
        return "sport" in str((source_match or {}).get("gameMode") or "").lower()

    def _find_focus_player(self, detail_root, *, query_full_id, query_bnet_id):
        for player in list(detail_root.get("teammateList") or []) + list(detail_root.get("enemyList") or []):
            if str(player.get("name") or "").strip() == str(query_full_id or "").strip():
                return dict(player)
            if str(player.get("bnetId") or "").strip() == str(query_bnet_id or "").strip():
                return dict(player)
        return {}

    def _match_result_text(self, match_data):
        return "Victory"


def _sample_detail_payload(focus_name: str, focus_bnet_id: str, other_name: str, other_bnet_id: str) -> dict[str, object]:
    return {
        "gameMode": "sport",
        "gameTimeSec": 905,
        "matchRet": 1,
        "heroList": [{"heroName": "Ana", "timePlayed": 905}],
        "teammateList": [
            {
                "name": focus_name,
                "bnetId": focus_bnet_id,
                "heroList": [{"heroName": "Ana", "timePlayed": 905}],
                "rankInfo": {"rankScore": 3010},
            },
            {
                "name": "Other#3333",
                "bnetId": "3333",
                "heroList": [{"heroName": "Reinhardt", "timePlayed": 905}],
                "rankInfo": {"rankScore": 2880},
            },
        ],
        "enemyList": [
            {
                "name": other_name,
                "bnetId": other_bnet_id,
                "heroList": [{"heroName": "Cassidy", "timePlayed": 905}],
                "rankInfo": {"rankScore": 2990},
            },
            {
                "name": "Enemy#4444",
                "bnetId": "4444",
                "heroList": [{"heroName": "Mercy", "timePlayed": 905}],
                "rankInfo": {"rankScore": 2800},
            },
        ],
    }


def _fake_image(tag: str) -> SimpleNamespace:
    return SimpleNamespace(content=str(tag).encode("utf-8"), media_type="image/png")


def _reply_image_bytes(reply: dict[str, object]) -> bytes:
    return base64.b64decode(str(reply.get("base64") or ""))


if __name__ == "__main__":
    unittest.main()
