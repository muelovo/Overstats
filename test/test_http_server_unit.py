from __future__ import annotations

import asyncio
import json
import base64
from pathlib import Path
from types import SimpleNamespace
import sys
import threading
import time
import unittest
from urllib.request import ProxyHandler, Request, build_opener, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
PARENT_DIR = REPO_ROOT.parent
for candidate in (PARENT_DIR, REPO_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from overstats.src.http_server import get_http_ui_bootstrap_payload, get_http_ui_module_specs, resolve_http_ui_asset
    import overstats.src.server as server_module
except ModuleNotFoundError:
    from src.http_server import get_http_ui_bootstrap_payload, get_http_ui_module_specs, resolve_http_ui_asset
    import src.server as server_module


class RegistryTests(unittest.TestCase):
    def test_common_modules_are_registered(self) -> None:
        modules = get_http_ui_module_specs()
        module_map = {item.id: item for item in modules}

        self.assertIn("dashen-profile", module_map)
        self.assertIn("dashen-match", module_map)
        self.assertIn("dashen-match-detail", module_map)
        self.assertIn("dashen-sameplay", module_map)
        self.assertIn("dashen-sameplay-detail", module_map)
        self.assertIn("dashen-summary-week", module_map)
        self.assertIn("ow-hero-pick-rate", module_map)
        self.assertIn("ow-shop", module_map)
        self.assertIn("patch-notes", module_map)
        self.assertFalse(module_map["ow-hero-pick-rate"].requires_target)
        self.assertFalse(module_map["ow-shop"].requires_target)
        self.assertFalse(module_map["patch-notes"].requires_target)
        self.assertTrue(module_map["dashen-profile"].requires_target)
        self.assertFalse(module_map["dashen-sameplay"].requires_target)
        self.assertFalse(module_map["dashen-sameplay-detail"].requires_target)
        self.assertNotIn("player-identity-search", module_map)
        self.assertEqual(module_map["dashen-summary-week"].json_endpoint, "/api/v2/dashen-summary/week")
        self.assertEqual(module_map["dashen-summary-week"].image_endpoint, "/api/v2/dashen-summary/week/image")
        self.assertEqual(module_map["dashen-match-detail"].json_endpoint, "/api/v2/dashen-match/detail/replies")
        self.assertEqual(module_map["dashen-sameplay"].json_endpoint, "/api/v2/dashen-sameplay")
        self.assertEqual(module_map["dashen-sameplay-detail"].json_endpoint, "/api/v2/dashen-sameplay/detail/replies")

    def test_module_field_specs_match_expected_payload_keys(self) -> None:
        modules = {item.id: item for item in get_http_ui_module_specs()}

        dashen_profile_fields = {field.id: field for field in modules["dashen-profile"].fields}
        patch_notes_fields = {field.id: field for field in modules["patch-notes"].fields}
        match_detail_fields = {field.id: field for field in modules["dashen-match-detail"].fields}
        sameplay_fields = {field.id: field for field in modules["dashen-sameplay"].fields}
        sameplay_detail_fields = {field.id: field for field in modules["dashen-sameplay-detail"].fields}
        hero_pick_rate_fields = {field.id: field for field in modules["ow-hero-pick-rate"].fields}

        self.assertEqual(dashen_profile_fields["profile_mode"].payload_key, "mode")
        self.assertEqual(patch_notes_fields["patch_kind"].payload_key, "patch_kind")
        self.assertEqual(patch_notes_fields["patch_kind"].default, "latest")
        self.assertEqual(match_detail_fields["analyze"].payload_key, "analyze")
        self.assertEqual(match_detail_fields["show_all_heroes"].payload_key, "show_all_heroes")
        self.assertEqual(sameplay_fields["player1_bnet_id"].payload_key, "player1_bnet_id")
        self.assertEqual(sameplay_fields["player2_bnet_id"].payload_key, "player2_bnet_id")
        self.assertEqual(sameplay_detail_fields["match_id"].payload_key, "match_id")
        self.assertEqual(sameplay_detail_fields["show_all_heroes"].payload_key, "show_all_heroes")
        self.assertEqual(sameplay_detail_fields["analyze"].payload_key, "analyze")
        self.assertEqual(hero_pick_rate_fields["view"].payload_key, "view")
        self.assertEqual(hero_pick_rate_fields["game_mode"].payload_key, "game_mode")
        self.assertEqual(hero_pick_rate_fields["mmr"].payload_key, "mmr")
        self.assertEqual(hero_pick_rate_fields["hero"].payload_key, "hero")
        self.assertEqual(hero_pick_rate_fields["history_limit"].payload_key, "history_limit")

    def test_bootstrap_payload_matches_registry(self) -> None:
        payload = get_http_ui_bootstrap_payload()

        self.assertIn("modules", payload)
        self.assertEqual(payload["default_module_id"], "dashen-profile")
        self.assertGreaterEqual(len(payload["modules"]), 13)


class AssetResponseTests(unittest.TestCase):
    def test_root_asset_contains_bootstrap_and_preview_layout(self) -> None:
        response = resolve_http_ui_asset("/")

        self.assertIsNotNone(response)
        self.assertEqual(response.content_type, "text/html; charset=utf-8")
        html = response.body.decode("utf-8")
        self.assertIn("Overstats 控制面板", html)
        self.assertIn('id="moduleNav"', html)
        self.assertIn('id="requestForm"', html)
        self.assertIn('id="jsonPreview"', html)
        self.assertIn('id="imagePreview"', html)
        self.assertIn('id="replyPreview"', html)
        self.assertIn("JSON 预览", html)
        self.assertIn("图片预览", html)
        self.assertIn("回复预览", html)
        self.assertIn("window.__OVERSTATS_UI_BOOTSTRAP__", html)
        self.assertIn("dashen-profile", html)
        self.assertIn("dashen-match-detail", html)
        self.assertIn("dashen-sameplay-detail", html)

    def test_static_assets_and_ui_health_exist(self) -> None:
        css_response = resolve_http_ui_asset("/ui/app.css")
        js_response = resolve_http_ui_asset("/ui/app.js")
        health_response = resolve_http_ui_asset("/ui/healthz")

        self.assertIsNotNone(css_response)
        self.assertIsNotNone(js_response)
        self.assertIsNotNone(health_response)
        self.assertIn("text/css", css_response.content_type)
        self.assertIn("application/javascript", js_response.content_type)
        self.assertIn("application/json", health_response.content_type)
        self.assertIsNone(resolve_http_ui_asset("/healthz"))

    def test_js_asset_contains_match_detail_reply_bundle_logic(self) -> None:
        response = resolve_http_ui_asset("/ui/app.js")

        self.assertIsNotNone(response)
        js_text = response.body.decode("utf-8")
        self.assertIn("MATCH_DETAIL_MODULE_ID", js_text)
        self.assertIn("SAMEPLAY_DETAIL_MODULE_ID", js_text)
        self.assertIn("getEffectiveEndpoint", js_text)
        self.assertIn("renderReplyPreview", js_text)
        self.assertIn("extractFirstImageReply", js_text)


class DashenRequestQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_when_pending_requests_hit_accept_limit(self) -> None:
        queue = server_module.DashenRequestQueue(max_concurrent_requests=1, max_accepted_requests=2)
        release_event = asyncio.Event()

        async def _slow_task() -> str:
            await release_event.wait()
            return "ok"

        first_task = asyncio.create_task(queue.run("first", _slow_task))
        await asyncio.sleep(0)

        second_task = asyncio.create_task(queue.run("second", _slow_task))
        for _ in range(50):
            if queue._queued_requests == 1:
                break
            await asyncio.sleep(0.01)
        else:
            self.fail("second task did not enter queue")

        with self.assertRaises(server_module.ModuleError) as ctx:
            await queue.run("third", _slow_task)

        self.assertEqual(ctx.exception.error, "too_many_requests")
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(ctx.exception.details["pending_requests"], 2)
        self.assertEqual(ctx.exception.details["max_accepted_requests"], 2)

        release_event.set()
        self.assertEqual(await first_task, "ok")
        self.assertEqual(await second_task, "ok")


class ServerRouteIntegrationTests(unittest.TestCase):
    def test_root_ui_routes_and_existing_api_route_work_together(self) -> None:
        original_load_query_tool = server_module.load_query_tool
        original_ensure_query_tool_assets = server_module.ensure_query_tool_assets
        original_request_metrics_recorder = server_module.RequestMetricsRecorder
        original_sync_service = server_module.OWHeroLeaderboardSyncService
        original_pick_rate_module = server_module.ow_hero_pick_rate_module
        original_ow_shop_module = server_module.ow_shop_module
        original_sameplay_module = server_module.dashen_sameplay_module
        original_player_identity_search_module = server_module.player_identity_search_module
        original_client_recorder = server_module.dashen_api_client.request_metrics_recorder

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
        server_module.ow_hero_pick_rate_module = _StubOWHeroPickRateModule()
        server_module.ow_shop_module = _StubOWShopModule()
        server_module.dashen_sameplay_module = _StubDashenSameplayModule()
        server_module.player_identity_search_module = _StubPlayerIdentitySearchModule()

        server = None
        thread = None
        try:
            config = server_module.APIConfig(
                host="127.0.0.1",
                port=0,
                use_stream_response=False,
                dashen_max_concurrent_requests=1,
                dashen_max_accepted_requests=4,
            )
            server = server_module.create_server(config)
            thread = threading.Thread(target=server.serve_forever, name="test-http-ui-server", daemon=True)
            thread.start()
            time.sleep(0.1)

            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            opener = build_opener(ProxyHandler({}))

            with opener.open(base_url + "/", timeout=10) as response:
                html_text = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("text/html", response.headers.get("Content-Type", ""))
                self.assertIn("Overstats 控制面板", html_text)

            with opener.open(base_url + "/ui/app.js", timeout=10) as response:
                js_text = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("application/javascript", response.headers.get("Content-Type", ""))
                self.assertIn("MATCH_DETAIL_MODULE_ID", js_text)
                self.assertIn("SAMEPLAY_DETAIL_MODULE_ID", js_text)

            with opener.open(base_url + "/ui/app.css", timeout=10) as response:
                css_text = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("text/css", response.headers.get("Content-Type", ""))
                self.assertIn(".app-shell", css_text)

            with opener.open(base_url + "/ui/healthz", timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload["service"], "overstats-http-ui")

            with opener.open(base_url + "/healthz", timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload["service"], "overstats-core")
                self.assertEqual(payload["dashen_max_accepted_requests"], 4)

            body = json.dumps({}).encode("utf-8")
            request = Request(
                base_url + "/api/v2/ow-shop",
                data=body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with opener.open(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["sections"][0]["title"], "Test Shop")

            pick_rate_body = json.dumps({"view": "ranking", "game_mode": "quick", "mmr": "all"}).encode("utf-8")
            pick_rate_request = Request(
                base_url + "/api/v2/ow-hero-pick-rate",
                data=pick_rate_body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with opener.open(pick_rate_request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["view"], "ranking")
                self.assertEqual(payload["heroes"][0]["hero_name"], "安娜")

            pick_rate_image_request = Request(
                base_url + "/api/v2/ow-hero-pick-rate/image",
                data=pick_rate_body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with opener.open(pick_rate_image_request, timeout=10) as response:
                image_body = response.read()
                self.assertEqual(response.status, 200)
                self.assertIn("image/png", response.headers.get("Content-Type", ""))
                self.assertEqual(image_body, b"pick-rate-image")

            identity_body = json.dumps({"bnet_id": "12345"}).encode("utf-8")
            identity_request = Request(
                base_url + "/api/v2/internal/player-identity/search",
                data=identity_body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with opener.open(identity_request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["query"]["bnet_id"], "12345")
                self.assertEqual(payload["candidates"], ["GrowlR#5632", "GrowlRAlt#9001"])
                self.assertEqual(payload["matches"][0]["match_type"], "exact")

            sameplay_body = json.dumps(
                {"player1_bnet_id": "Alpha#1111", "player2_bnet_id": "Bravo#2222", "limit": 1}
            ).encode("utf-8")
            sameplay_request = Request(
                base_url + "/api/v2/dashen-sameplay",
                data=sameplay_body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with opener.open(sameplay_request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["players"]["resolved"]["player1"]["full_id"], "Alpha#1111")
                self.assertEqual(payload["customer_tokens"]["player2"], "token-bravo")
                self.assertEqual(payload["summary"]["total_common_count"], 1)
                self.assertEqual(payload["matches"][0]["matchId"], "m2")

            sameplay_list_replies_request = Request(
                base_url + "/api/v2/dashen-sameplay/replies",
                data=sameplay_body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with opener.open(sameplay_list_replies_request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["replies"][0]["meta_type"], "ds_sameplay_list")
                self.assertEqual(payload["replies"][1]["type"], "image")

            sameplay_replies_body = json.dumps(
                {
                    "player1_customer_token": "token-alpha",
                    "player2_customer_token": "token-bravo",
                    "match_id": "m2",
                    "show_all_heroes": True,
                    "analyze": True,
                }
            ).encode("utf-8")
            sameplay_replies_request = Request(
                base_url + "/api/v2/dashen-sameplay/detail/replies",
                data=sameplay_replies_body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with opener.open(sameplay_replies_request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["match_id"], "m2")
                self.assertEqual(payload["replies"][0]["meta_type"], "ds_match_detail_players")
                self.assertEqual(payload["replies"][1]["type"], "image")

            sameplay_image_body = json.dumps(
                {"player1_bnet_id": "Alpha#1111", "player2_bnet_id": "Bravo#2222", "index": 0}
            ).encode("utf-8")
            sameplay_image_request = Request(
                base_url + "/api/v2/dashen-sameplay/detail/image",
                data=sameplay_image_body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with opener.open(sameplay_image_request, timeout=10) as response:
                image_body = response.read()
                self.assertEqual(response.status, 200)
                self.assertIn("image/png", response.headers.get("Content-Type", ""))
                self.assertEqual(image_body, b"sameplay-main-image")
        finally:
            if server is not None:
                try:
                    server.shutdown()
                except Exception:
                    pass
                try:
                    server.server_close()
                except Exception:
                    pass
            if thread is not None:
                thread.join(timeout=2)
            server_module.load_query_tool = original_load_query_tool
            server_module.ensure_query_tool_assets = original_ensure_query_tool_assets
            server_module.RequestMetricsRecorder = original_request_metrics_recorder
            server_module.OWHeroLeaderboardSyncService = original_sync_service
            server_module.ow_hero_pick_rate_module = original_pick_rate_module
            server_module.ow_shop_module = original_ow_shop_module
            server_module.dashen_sameplay_module = original_sameplay_module
            server_module.player_identity_search_module = original_player_identity_search_module
            server_module.dashen_api_client.request_metrics_recorder = original_client_recorder


class _StubRequestMetricsRecorder:
    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def enqueue(self, url, source_type, success):  # noqa: ANN001
        return None


class _StubSyncService:
    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None


class _StubOWShopOutput:
    def to_dict(self):
        return {
            "ok": True,
            "generated_at": "2026-04-29 12:34:56",
            "cache_ttl_seconds": 900,
            "sections": [
                {
                    "title": "Test Shop",
                    "expires_text": "",
                    "item_count": 0,
                    "items": [],
                }
            ],
        }


class _StubOWShopImage:
    content = b"stub-image"


class _StubOWShopModule:
    async def query_shop(self, *, render=False):
        if render:
            output = _StubOWShopOutput()
            output.image = _StubOWShopImage()
            return output
        return _StubOWShopOutput()


class _StubOWHeroPickRateOutput:
    def __init__(self, *, with_image: bool = False) -> None:
        self.image = _StubOWHeroPickRateImage() if with_image else None

    def to_dict(self):
        return {
            "ok": True,
            "view": "ranking",
            "region": "cn",
            "game_mode": "quick",
            "mmr": "all",
            "snapshot": {
                "season": 2,
                "ds": "2026-04-29",
                "hero_count": 1,
            },
            "heroes": [
                {
                    "rank": 1,
                    "hero_guid": "ana",
                    "hero_name": "安娜",
                    "hero_role": "support",
                    "selection_ratio": 7.1,
                    "ban_ratio": 0.0,
                    "win_ratio": 51.2,
                    "kda": 4.2,
                    "icon_url": "",
                }
            ],
        }


class _StubOWHeroPickRateImage:
    content = b"pick-rate-image"


class _StubOWHeroPickRateModule:
    async def query_pick_rate(self, query, *, render=False):  # noqa: ANN001
        return _StubOWHeroPickRateOutput(with_image=render)


class _StubDashenSameplayPlayer:
    def __init__(self, full_id, bnet_id, customer_token):  # noqa: ANN001
        self.full_id = full_id
        self.bnet_id = bnet_id
        self.customer_token = customer_token

    def to_dict(self):
        return {
            "query": self.full_id,
            "full_id": self.full_id,
            "bnet_id": self.bnet_id,
            "customer_token": self.customer_token,
            "has_customer_token": bool(self.customer_token),
        }


class _StubDashenSameplayImage:
    def __init__(self, content):  # noqa: ANN001
        self.content = content
        self.media_type = "image/png"


class _StubDashenSameplayModule:
    def __init__(self) -> None:
        self.player1 = _StubDashenSameplayPlayer("Alpha#1111", "1111", "token-alpha")
        self.player2 = _StubDashenSameplayPlayer("Bravo#2222", "2222", "token-bravo")

    async def query_sameplay_list(self, query, *, render=False):  # noqa: ANN001
        return SimpleNamespace(
            player1=self.player1,
            player2=self.player2,
            summary={
                "total_common_count": 1,
                "returned_count": 1,
                "quick_count": 0,
                "competitive_count": 1,
                "scanned_count": 4,
            },
            matches=[{"matchId": "m2", "beginTs": 200, "gameMode": "sport"}],
            image=_StubDashenSameplayImage(b"sameplay-list-image") if render else None,
        )

    async def query_sameplay_list_replies(self, query):  # noqa: ANN001
        return SimpleNamespace(
            player1=self.player1,
            player2=self.player2,
            summary={
                "total_common_count": 1,
                "returned_count": 1,
                "quick_count": 0,
                "competitive_count": 1,
                "scanned_count": 4,
            },
            replies=[
                {
                    "type": "meta",
                    "meta_type": "ds_sameplay_list",
                    "data": {
                        "context_type": "ds_sameplay_list",
                        "players": {"player1": self.player1.to_dict(), "player2": self.player2.to_dict()},
                        "customer_tokens": {
                            "player1": self.player1.customer_token,
                            "player2": self.player2.customer_token,
                        },
                        "summary": {
                            "total_common_count": 1,
                            "returned_count": 1,
                            "quick_count": 0,
                            "competitive_count": 1,
                            "scanned_count": 4,
                        },
                        "match_entries": [{"matchId": "m2", "beginTs": 200, "gameMode": "sport"}],
                    },
                },
                {
                    "type": "image",
                    "media_type": "image/png",
                    "base64": base64.b64encode(b"sameplay-list-image").decode("ascii"),
                },
            ],
            matches=[{"matchId": "m2", "beginTs": 200, "gameMode": "sport"}],
        )

    async def query_sameplay_detail(self, query, *, match_id="", render=True, **kwargs):  # noqa: ANN001
        return SimpleNamespace(
            player1=self.player1,
            player2=self.player2,
            summary={
                "total_common_count": 1,
                "returned_count": 1,
                "quick_count": 0,
                "competitive_count": 1,
                "scanned_count": 4,
            },
            matches=[{"matchId": match_id or "m2", "beginTs": 200, "gameMode": "sport"}],
            source_match={"matchId": match_id or "m2", "beginTs": 200, "gameMode": "sport"},
            match_id=match_id or "m2",
            match_kind="normal",
            detail={"data": {"gameMode": "sport", "teammateList": [], "enemyList": []}},
            main_image=_StubDashenSameplayImage(b"sameplay-main-image") if render else None,
            main_detail_source_player=1,
            player_details=[],
            waterfall_image=None,
            analysis_image=None,
            notes=[],
        )

    async def query_sameplay_detail_replies(self, query, *, match_id="", **kwargs):  # noqa: ANN001
        return SimpleNamespace(
            player1=self.player1,
            player2=self.player2,
            summary={
                "total_common_count": 1,
                "returned_count": 1,
                "quick_count": 0,
                "competitive_count": 1,
                "scanned_count": 4,
            },
            replies=[
                {
                    "type": "meta",
                    "meta_type": "ds_match_detail_players",
                    "data": {
                        "context_type": "ds_match_detail_players",
                        "player_ids": ["Alpha#1111", "Bravo#2222"],
                        "competitive": True,
                    },
                },
                {
                    "type": "image",
                    "media_type": "image/png",
                    "base64": base64.b64encode(b"sameplay-main-image").decode("ascii"),
                },
            ],
            matches=[{"matchId": match_id or "m2", "beginTs": 200, "gameMode": "sport"}],
            match_id=match_id or "m2",
            match_kind="normal",
        )


class _StubPlayerIdentityMatch:
    def __init__(self, bnet_id, battletag, battlename, battlenum, update_time, match_type):  # noqa: ANN001
        self.bnet_id = bnet_id
        self.battletag = battletag
        self.battlename = battlename
        self.battlenum = battlenum
        self.update_time = update_time
        self.match_type = match_type

    def to_dict(self):
        return {
            "bnet_id": self.bnet_id,
            "battletag": self.battletag,
            "battlename": self.battlename,
            "battlenum": self.battlenum,
            "update_time": self.update_time,
            "match_type": self.match_type,
        }


class _StubPlayerIdentitySearchOutput:
    def __init__(self, query, matches):  # noqa: ANN001
        self.query = query
        self.matches = tuple(matches)


class _StubPlayerIdentitySearchModule:
    async def search(self, query):  # noqa: ANN001
        return _StubPlayerIdentitySearchOutput(
            query=query,
            matches=(
                _StubPlayerIdentityMatch("12345", "GrowlR#5632", "GrowlR", "5632", 1714464000, "exact"),
                _StubPlayerIdentityMatch("123456", "GrowlRAlt#9001", "GrowlRAlt", "9001", 1714463000, "prefix"),
            ),
        )


if __name__ == "__main__":
    unittest.main()
