from __future__ import annotations

import asyncio
import datetime as dt
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
PARENT_DIR = REPO_ROOT.parent
for candidate in (PARENT_DIR, REPO_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from overstats.src.db import (
        HERO_LEADERBOARD_CN_TABLE,
        HERO_LEADERBOARD_GLOBAL_TABLE,
        OWHeroLeaderboardDB,
    )
    from overstats.src.modules.ow_hero_leaderboard import (
        CN_GAME_MODES,
        CN_MMRS,
        OWHeroLeaderboardRequests,
        OWHeroLeaderboardRow,
        OWHeroLeaderboardSyncService,
        OWHeroLeaderboardTarget,
    )
    import overstats.src.server as server_module
except ModuleNotFoundError:
    from src.db import (
        HERO_LEADERBOARD_CN_TABLE,
        HERO_LEADERBOARD_GLOBAL_TABLE,
        OWHeroLeaderboardDB,
    )
    from src.modules.ow_hero_leaderboard import (
        CN_GAME_MODES,
        CN_MMRS,
        OWHeroLeaderboardRequests,
        OWHeroLeaderboardRow,
        OWHeroLeaderboardSyncService,
        OWHeroLeaderboardTarget,
    )
    import src.server as server_module


BEIJING = ZoneInfo("Asia/Shanghai")


def _sample_row(
    *,
    game_mode: str = "kuaisu",
    mmr: str = "-127",
    hero_id: str = "ana",
    selection_ratio: float = 6.79,
    ban_ratio: float = 0.0,
    win_ratio: float = 48.82,
    kda: float = 3.87,
    ds: str = "2026-04-28",
) -> OWHeroLeaderboardRow:
    return OWHeroLeaderboardRow(
        season=2,
        ds=ds,
        game_mode=game_mode,
        mmr=mmr,
        hero_id=hero_id,
        hero_type="3",
        selection_ratio=selection_ratio,
        ban_ratio=ban_ratio,
        win_ratio=win_ratio,
        kda=kda,
    )


class RequestNormalizationTests(unittest.TestCase):
    def test_normalize_payload_preserves_all_metrics(self) -> None:
        requests = OWHeroLeaderboardRequests()
        target = OWHeroLeaderboardTarget(season=2, game_mode="kuaisu", mmr="-127")
        payload = {
            "code": 0,
            "message": "success",
            "data": [
                {
                    "hero_id": "ana",
                    "hero_type": "3",
                    "selection_ratio": 6.79,
                    "ban_ratio": 0,
                    "win_ratio": 48.82,
                    "kda": 3.87,
                    "ds": "2026-04-28",
                }
            ],
        }

        rows = requests.normalize_payload(payload, target)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].hero_id, "ana")
        self.assertEqual(rows[0].hero_type, "3")
        self.assertEqual(rows[0].selection_ratio, 6.79)
        self.assertEqual(rows[0].ban_ratio, 0.0)
        self.assertEqual(rows[0].win_ratio, 48.82)
        self.assertEqual(rows[0].kda, 3.87)
        self.assertEqual(rows[0].ds, "2026-04-28")
        self.assertEqual(rows[0].season, 2)
        self.assertEqual(rows[0].game_mode, "kuaisu")
        self.assertEqual(rows[0].mmr, "-127")

    def test_cn_targets_match_overshop_matrix(self) -> None:
        requests = OWHeroLeaderboardRequests()

        targets = requests.build_cn_targets(season=2)

        self.assertEqual(len(targets), len(CN_GAME_MODES) * len(CN_MMRS))
        self.assertEqual(
            [(target.game_mode, target.mmr) for target in targets],
            [(game_mode, mmr) for game_mode in CN_GAME_MODES for mmr in CN_MMRS],
        )
        self.assertTrue(all(target.season == 2 for target in targets))


class DatabaseTests(unittest.TestCase):
    def test_initialize_creates_both_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "leaderboard.sqlite3"
            db = OWHeroLeaderboardDB(db_path=db_path)
            db.initialize_database()

            connection = sqlite3.connect(db_path)
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
            finally:
                connection.close()

        self.assertIn(HERO_LEADERBOARD_CN_TABLE, tables)
        self.assertIn(HERO_LEADERBOARD_GLOBAL_TABLE, tables)

    def test_upsert_updates_existing_row_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = OWHeroLeaderboardDB(db_path=Path(temp_dir) / "leaderboard.sqlite3")
            first_row = _sample_row(win_ratio=48.82)
            second_row = _sample_row(win_ratio=51.11)

            inserted = db.upsert_rows(
                HERO_LEADERBOARD_CN_TABLE,
                [first_row],
                updated_at="2026-04-29T00:00:00+00:00",
            )
            updated = db.upsert_rows(
                HERO_LEADERBOARD_CN_TABLE,
                [second_row],
                updated_at="2026-04-29T01:00:00+00:00",
            )
            rows = db.fetch_rows(
                HERO_LEADERBOARD_CN_TABLE,
                season=2,
                ds="2026-04-28",
                game_mode="kuaisu",
                mmr="-127",
                hero_id="ana",
            )

        self.assertEqual(inserted, 1)
        self.assertEqual(updated, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["win_ratio"], 51.11)
        self.assertEqual(rows[0]["created_at"], "2026-04-29T00:00:00+00:00")
        self.assertEqual(rows[0]["updated_at"], "2026-04-29T01:00:00+00:00")


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_once_persists_cn_and_skips_global(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = OWHeroLeaderboardDB(db_path=Path(temp_dir) / "leaderboard.sqlite3")
            requests = _StubLeaderboardRequests(
                targets=(
                    OWHeroLeaderboardTarget(season=2, game_mode="kuaisu", mmr="-127"),
                    OWHeroLeaderboardTarget(season=2, game_mode="jingji", mmr="Gold"),
                ),
                responses={
                    ("kuaisu", "-127"): (_sample_row(game_mode="kuaisu", mmr="-127", hero_id="ana"),),
                    ("jingji", "Gold"): (_sample_row(game_mode="jingji", mmr="Gold", hero_id="sombra"),),
                },
            )
            service = OWHeroLeaderboardSyncService(
                requests=requests,
                db=db,
                now_provider=lambda: dt.datetime(2026, 4, 29, 10, 0, tzinfo=BEIJING),
            )

            results = await service.sync_once()
            cn_rows = db.fetch_rows(HERO_LEADERBOARD_CN_TABLE)
            global_rows = db.fetch_rows(HERO_LEADERBOARD_GLOBAL_TABLE)

        self.assertEqual(results["cn"].status, "ok")
        self.assertEqual(results["cn"].rows_written, 2)
        self.assertEqual(results["global"].status, "skipped_not_implemented")
        self.assertEqual(len(cn_rows), 2)
        self.assertEqual(global_rows, [])

    async def test_sync_once_records_partial_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = OWHeroLeaderboardDB(db_path=Path(temp_dir) / "leaderboard.sqlite3")
            requests = _StubLeaderboardRequests(
                targets=(
                    OWHeroLeaderboardTarget(season=2, game_mode="kuaisu", mmr="-127"),
                    OWHeroLeaderboardTarget(season=2, game_mode="jingji", mmr="Gold"),
                ),
                responses={
                    ("kuaisu", "-127"): (_sample_row(game_mode="kuaisu", mmr="-127"),),
                },
                failures={("jingji", "Gold"): RuntimeError("boom")},
            )
            service = OWHeroLeaderboardSyncService(
                requests=requests,
                db=db,
                now_provider=lambda: dt.datetime(2026, 4, 29, 10, 0, tzinfo=BEIJING),
            )

            result = await service.sync_cn_once()
            rows = db.fetch_rows(HERO_LEADERBOARD_CN_TABLE)

        self.assertEqual(result.status, "partial_failure")
        self.assertEqual(result.rows_written, 1)
        self.assertEqual(result.failed_targets, 1)
        self.assertEqual(len(rows), 1)
        self.assertTrue(result.failures)
        self.assertIn("jingji:Gold", result.failures[0])

    async def test_start_triggers_immediate_sync(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = OWHeroLeaderboardDB(db_path=Path(temp_dir) / "leaderboard.sqlite3")
            requests = _StubLeaderboardRequests(
                targets=(OWHeroLeaderboardTarget(season=2, game_mode="kuaisu", mmr="-127"),),
                responses={("kuaisu", "-127"): (_sample_row(),)},
            )
            service = OWHeroLeaderboardSyncService(
                requests=requests,
                db=db,
                now_provider=lambda: dt.datetime(2026, 4, 29, 10, 0, tzinfo=BEIJING),
            )

            await service.start()
            await asyncio.wait_for(_wait_for_row_count(db, HERO_LEADERBOARD_CN_TABLE, 1), timeout=1.0)
            await service.close()

        self.assertTrue(requests.fetch_calls)
        self.assertIsNone(service._task)

    def test_next_scheduled_run_uses_next_beijing_noon(self) -> None:
        before_noon = dt.datetime(2026, 4, 29, 10, 30, tzinfo=BEIJING)
        exact_noon = dt.datetime(2026, 4, 29, 12, 0, tzinfo=BEIJING)

        next_before_noon = OWHeroLeaderboardSyncService.next_scheduled_run_at(before_noon)
        next_exact_noon = OWHeroLeaderboardSyncService.next_scheduled_run_at(exact_noon)

        self.assertEqual(next_before_noon, dt.datetime(2026, 4, 29, 12, 0, tzinfo=BEIJING))
        self.assertEqual(next_exact_noon, dt.datetime(2026, 4, 30, 12, 0, tzinfo=BEIJING))

    async def test_close_cancels_background_task_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = OWHeroLeaderboardDB(db_path=Path(temp_dir) / "leaderboard.sqlite3")
            requests = _StubLeaderboardRequests(
                targets=(OWHeroLeaderboardTarget(season=2, game_mode="kuaisu", mmr="-127"),),
                responses={("kuaisu", "-127"): (_sample_row(),)},
            )
            service = OWHeroLeaderboardSyncService(
                requests=requests,
                db=db,
                now_provider=lambda: dt.datetime(2026, 4, 29, 10, 0, tzinfo=BEIJING),
            )

            await service.start()
            await asyncio.wait_for(_wait_for_row_count(db, HERO_LEADERBOARD_CN_TABLE, 1), timeout=1.0)
            await service.close()

        self.assertIsNone(service._task)


class ServerLifecycleTests(unittest.TestCase):
    def test_create_server_starts_and_closes_sync_service(self) -> None:
        original_load_query_tool = server_module.load_query_tool
        original_ensure_query_tool_assets = server_module.ensure_query_tool_assets
        original_request_metrics_recorder = server_module.RequestMetricsRecorder
        original_sync_service = server_module.OWHeroLeaderboardSyncService
        original_client_recorder = server_module.dashen_api_client.request_metrics_recorder

        _StubSyncService.last_instance = None
        server_module.load_query_tool = lambda: {}
        server_module.ensure_query_tool_assets = lambda _config: {
            "checked": 0,
            "cached": 0,
            "downloaded": 0,
            "failed": 0,
            "asset_dir": ".",
        }
        server_module.RequestMetricsRecorder = _StubRequestMetricsRecorder
        server_module.OWHeroLeaderboardSyncService = _StubSyncService

        server = None
        try:
            config = server_module.APIConfig(
                host="127.0.0.1",
                port=0,
                use_stream_response=False,
                dashen_max_concurrent_requests=1,
            )
            server = server_module.create_server(config)
            self.assertIsNotNone(_StubSyncService.last_instance)
            self.assertTrue(_StubSyncService.last_instance.start_called)
            server.server_close()
            self.assertTrue(_StubSyncService.last_instance.close_called)
            server = None
        finally:
            if server is not None:
                try:
                    server.server_close()
                except Exception:
                    pass
            server_module.load_query_tool = original_load_query_tool
            server_module.ensure_query_tool_assets = original_ensure_query_tool_assets
            server_module.RequestMetricsRecorder = original_request_metrics_recorder
            server_module.OWHeroLeaderboardSyncService = original_sync_service
            server_module.dashen_api_client.request_metrics_recorder = original_client_recorder


class _StubLeaderboardRequests:
    def __init__(self, *, targets, responses=None, failures=None) -> None:
        self._targets = tuple(targets)
        self._responses = dict(responses or {})
        self._failures = dict(failures or {})
        self.fetch_calls = []

    def build_cn_targets(self, season=None):  # noqa: ANN001
        return self._targets

    async def fetch_cn_target(self, target, *, client=None):  # noqa: ANN001
        key = (target.game_mode, target.mmr)
        self.fetch_calls.append(key)
        if key in self._failures:
            raise self._failures[key]
        return tuple(self._responses.get(key, ()))


async def _wait_for_row_count(db: OWHeroLeaderboardDB, table_name: str, expected_count: int) -> None:
    deadline = asyncio.get_running_loop().time() + 1.0
    while True:
        if db.count_rows(table_name) >= expected_count:
            return
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError(f"Timed out waiting for {expected_count} rows in {table_name}.")
        await asyncio.sleep(0.01)


class _StubRequestMetricsRecorder:
    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def enqueue(self, url, source_type, success):  # noqa: ANN001
        return None


class _StubSyncService:
    last_instance = None

    def __init__(self) -> None:
        self.start_called = False
        self.close_called = False
        type(self).last_instance = self

    async def start(self) -> None:
        self.start_called = True

    async def close(self) -> None:
        self.close_called = True


if __name__ == "__main__":
    unittest.main()
