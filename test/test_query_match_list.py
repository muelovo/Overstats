import asyncio
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from overstats.src.client.apiclient import DashenAPIClient, dashen_api_client
from overstats.src.modules.bnet_search import BnetSearchModule
from overstats.src.modules.dashen_summary.runtime.dashen import get_live_dashen_season


bnet_id = "oL1ama#5684"
customer_token = ""
test_dir = Path(__file__).resolve().parent


class RecordingClient:
    def __init__(self, inner_client: Any) -> None:
        self.inner_client = inner_client
        self.history: List[Dict[str, Any]] = []

    async def request(self, method: str, url: str, *, log_context=None, **kwargs):
        response = await self.inner_client.request(method, url, log_context=log_context, **kwargs)
        record = {
            "method": method,
            "url": url,
            "log_context": log_context,
            "headers": dict(kwargs.get("headers") or {}),
            "json": kwargs.get("json"),
            "params": dict(kwargs.get("params") or {}),
            "status_code": response.status_code,
            "response_headers": dict(response.headers),
            "response_text": response.text,
        }
        self.history.append(record)
        return response

    async def get(self, url: str, *, log_context=None, **kwargs):
        return await self.request("GET", url, log_context=log_context, **kwargs)

    async def post(self, url: str, *, log_context=None, **kwargs):
        return await self.request("POST", url, log_context=log_context, **kwargs)

    async def aclose(self) -> None:
        await self.inner_client.aclose()


async def _resolve_customer_token(search_module: BnetSearchModule) -> str:
    if customer_token:
        return customer_token
    search_output = await search_module.search(bnet_id, render=False)
    token = search_output.result.customer_token
    print("search result:")
    print(
        json.dumps(
            {
                "query": search_output.result.query,
                "customer_token": token,
                "bnet_id": search_output.result.bnet_id,
                "full_id": search_output.result.full_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not token:
        raise RuntimeError("Failed to resolve customer_token from bnet search.")
    return token


async def main() -> None:
    recorded_netease_client = RecordingClient(dashen_api_client.netease_client)
    recorded_proxy_client = RecordingClient(dashen_api_client.proxy_client)
    api_client = DashenAPIClient(
        netease_client=recorded_netease_client,
        proxy_client=recorded_proxy_client,
        client_config=dashen_api_client.client_config,
    )
    search_module = BnetSearchModule(api_client)
    token = await _resolve_customer_token(search_module)

    live_season = get_live_dashen_season()
    cases = [
        ("sport-current", lambda: api_client.query_match_list(token, "sport", page=1, season=None)),
        ("sport-live-season", lambda: api_client.query_match_list(token, "sport", page=1, season=live_season)),
        ("leisure-current", lambda: api_client.query_match_list(token, "leisure", page=1, season=None)),
        ("leisure-live-season", lambda: api_client.query_match_list(token, "leisure", page=1, season=live_season)),
        ("quick-fight-current", lambda: api_client.fight_query_match_list(token, "QuickFight", page=1, season=None)),
        ("sport-fight-current", lambda: api_client.fight_query_match_list(token, "SportFight", page=1, season=None)),
    ]

    start_index = len(recorded_netease_client.history)
    results: List[Dict[str, Any]] = []
    for name, runner in cases:
        try:
            payload = await runner()
        except Exception as exc:
            payload = {
                "exception": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            }

        request_record = None
        if len(recorded_netease_client.history) > start_index:
            request_record = recorded_netease_client.history[start_index]
            start_index += 1

        item = {
            "case": name,
            "request": request_record,
            "payload": payload,
        }
        results.append(item)

    output_path = test_dir / "query-match-list-debug.json"
    output_path.write_text(
        json.dumps(
            {
                "bnet_id": bnet_id,
                "customer_token": token,
                "live_season": live_season,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"saved: {output_path}")

    for item in results:
        print("=" * 24)
        print(item["case"])
        print("request:")
        print(json.dumps(item["request"], ensure_ascii=False, indent=2))
        print("payload:")
        print(json.dumps(item["payload"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
