import asyncio
import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from overstats.src.client.apiclient import DashenAPIClient, dashen_api_client
from overstats.src.modules.bnet_search import BnetSearchModule


bnet_id = "oL1ama#5684"
test_dir = Path(__file__).resolve().parent


class RecordingClient:
    def __init__(self, inner_client: Any) -> None:
        self.inner_client = inner_client
        self.last_request: Optional[Dict[str, Any]] = None

    async def request(self, method: str, url: str, *, log_context=None, **kwargs):
        self.last_request = {
            "method": method,
            "url": url,
            "log_context": log_context,
            "headers": dict(kwargs.get("headers") or {}),
            "json": kwargs.get("json"),
            "params": dict(kwargs.get("params") or {}),
        }
        return await self.inner_client.request(method, url, log_context=log_context, **kwargs)

    async def get(self, url: str, *, log_context=None, **kwargs):
        return await self.request("GET", url, log_context=log_context, **kwargs)

    async def post(self, url: str, *, log_context=None, **kwargs):
        return await self.request("POST", url, log_context=log_context, **kwargs)

    async def aclose(self) -> None:
        await self.inner_client.aclose()


async def main() -> None:
    recorded_netease_client = RecordingClient(dashen_api_client.netease_client)
    recorded_proxy_client = RecordingClient(dashen_api_client.proxy_client)
    api_client = DashenAPIClient(
        netease_client=recorded_netease_client,
        proxy_client=recorded_proxy_client,
        client_config=dashen_api_client.client_config,
    )
    search_module = BnetSearchModule(api_client)

    output = await search_module.search(bnet_id, render=False)
    result = output.result
    output_payload = {
        "query": result.query,
        "customer_token": result.customer_token,
        "bnet_id": result.bnet_id,
        "full_id": result.full_id,
        "icon_url": result.icon_url,
        "payload": result.payload,
    }

    output_path = test_dir / "bnet-search.json"
    output_path.write_text(
        json.dumps(output_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved: {output_path}")
    if recorded_netease_client.last_request:
        print("request:")
        print(json.dumps(recorded_netease_client.last_request, ensure_ascii=False, indent=2))
    print("raw payload:")
    print(json.dumps(result.payload, ensure_ascii=False, indent=2))
    print("parsed fields:")
    print(
        json.dumps(
            {
                "query": result.query,
                "customer_token": result.customer_token,
                "bnet_id": result.bnet_id,
                "full_id": result.full_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
