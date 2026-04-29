import json
from pathlib import Path
from urllib.request import Request, urlopen


base_url = "http://127.0.0.1:18080"
test_dir = Path(__file__).resolve().parent

for payload, suffix in (
    ({}, "latest"),
    ({"patch_kind": "small"}, "small"),
    ({"patch_kind": "big"}, "big"),
):
    body = json.dumps(payload).encode("utf-8")

    json_request = Request(
        f"{base_url}/api/v2/patch-notes",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(json_request, timeout=120) as response:
        json_path = test_dir / f"patch-notes-{suffix}.json"
        json_path.write_bytes(response.read())
        print(f"saved: {json_path}")

    image_request = Request(
        f"{base_url}/api/v2/patch-notes/image",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(image_request, timeout=120) as response:
        image_path = test_dir / f"patch-notes-{suffix}.png"
        image_path.write_bytes(response.read())
        print(f"saved: {image_path}")
