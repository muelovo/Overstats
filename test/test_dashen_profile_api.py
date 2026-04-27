import json
from pathlib import Path
from urllib.request import Request, urlopen


base_url = "http://127.0.0.1:18080"
bnet_id = "GrowlR#5632"
season = 22
test_dir = Path(__file__).resolve().parent

cases = [
    (
        "dashen-profile-quick.json",
        "/api/v2/dashen-profile",
        {"bnet_id": bnet_id},
    ),
    (
        "dashen-profile-quick.png",
        "/api/v2/dashen-profile/image",
        {"bnet_id": bnet_id},
    ),
    (
        "dashen-profile-competitive.png",
        "/api/v2/dashen-profile/image",
        {"bnet_id": bnet_id, "competitive": True},
    ),
    (
        "dashen-profile-season.json",
        "/api/v2/dashen-profile",
        {"bnet_id": bnet_id, "season": season},
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
