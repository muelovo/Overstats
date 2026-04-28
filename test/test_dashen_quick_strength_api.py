import json
from pathlib import Path
from urllib.request import Request, urlopen


base_url = "http://127.0.0.1:18080"
bnet_id = "oL1ama#5684"
test_dir = Path(__file__).resolve().parent

cases = [
    # (
    #     "dashen-quick-strength.json",
    #     "/api/v2/dashen-quick-strength",
    #     {"bnet_id": bnet_id, "limit": 12},
    # ),
    (
        "dashen-quick-strength.png",
        "/api/v2/dashen-quick-strength/image",
        {"bnet_id": bnet_id, "limit": 12},
    ),
]

for filename, path, payload in cases:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        f"{base_url}{path}",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        output_path = test_dir / filename
        output_path.write_bytes(response.read())
        print(f"saved: {output_path}")
