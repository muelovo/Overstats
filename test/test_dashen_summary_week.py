import json
from pathlib import Path
from urllib.request import Request, urlopen


base_url = "http://127.0.0.1:18080"
bnet_id = "oL1ama#5684"
scope = "week"
test_dir = Path(__file__).resolve().parent
body = json.dumps({"bnet_id": bnet_id}).encode("utf-8")


json_request = Request(
    f"{base_url}/api/v2/dashen-summary/{scope}",
    data=body,
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST",
)
with urlopen(json_request, timeout=120) as response:
    json_path = test_dir / f"dashen-summary-{scope}.json"
    json_path.write_bytes(response.read())
    print(f"saved: {json_path}")


image_request = Request(
    f"{base_url}/api/v2/dashen-summary/{scope}/image",
    data=body,
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST",
)
with urlopen(image_request, timeout=120) as response:
    image_path = test_dir / f"dashen-summary-{scope}.jpg"
    image_path.write_bytes(response.read())
    print(f"saved: {image_path}")
