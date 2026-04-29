from __future__ import annotations

from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
PARENT_DIR = REPO_ROOT.parent
for candidate in (PARENT_DIR, REPO_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from overstats.src.modules.errors import ModuleError
    from overstats.src.modules.ow_shop.render import RenderedImage, render_ow_shop
    from overstats.src.modules.ow_shop.requests import OWShopItem, OWShopRequests, OWShopSection, SHOP_SECTION_SOURCES
    from overstats.src.modules.ow_shop.service import OWShopModule, OWShopOutput
    import overstats.src.server as server_module
except ModuleNotFoundError:
    from src.modules.errors import ModuleError
    from src.modules.ow_shop.render import RenderedImage, render_ow_shop
    from src.modules.ow_shop.requests import OWShopItem, OWShopRequests, OWShopSection, SHOP_SECTION_SOURCES
    from src.modules.ow_shop.service import OWShopModule, OWShopOutput
    import src.server as server_module


class RequestNormalizationTests(unittest.TestCase):
    def test_page_payload_normalizes_section(self) -> None:
        requests = OWShopRequests(now_ms_factory=lambda: 0)
        payload = {
            "expiresAtMs": (3 * 24 * 60 + 4 * 60 + 12) * 60 * 1000,
            "mtxCollections": [
                {
                    "items": [
                        {
                            "title": "测试礼包™",
                            "description": "传奇 | 礼包（10件物品）",
                            "productIds": [101, 102, 103],
                            "price": {"raw": 1900.0, "currency": "XWC", "discountPercentage": 50},
                            "image": {"url": "//catalog.blzstatic.cn/example.png"},
                        }
                    ]
                }
            ],
        }

        section = requests.normalize_section_payload(SHOP_SECTION_SOURCES[0], payload)

        self.assertEqual(section.title, SHOP_SECTION_SOURCES[0].title)
        self.assertEqual(section.expires_text, "3天4小时12分")
        self.assertEqual(len(section.items), 1)
        self.assertEqual(section.items[0].title, "测试礼包")
        self.assertEqual(section.items[0].image_url, "https://catalog.blzstatic.cn/example.png")
        self.assertEqual(section.items[0].price_discount_percentage, 50)
        self.assertEqual(section.items[0].price_raw, 1900)

    def test_array_payload_normalizes_section(self) -> None:
        requests = OWShopRequests()
        payload = [
            {
                "title": "补给",
                "description": "补给",
                "productIds": [201],
                "price": {"raw": 1000.0, "currency": "XVT", "discountPercentage": None},
                "image": {"url": "https://contentstack-images.blzstatic.cn/loot-box.png"},
            }
        ]

        section = requests.normalize_section_payload(SHOP_SECTION_SOURCES[3], payload)

        self.assertEqual(section.title, SHOP_SECTION_SOURCES[3].title)
        self.assertEqual(section.expires_text, "")
        self.assertEqual(len(section.items), 1)
        self.assertEqual(section.items[0].price_currency, "XVT")
        self.assertEqual(section.items[0].price_discount_percentage, 0)


class ShopModuleTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_uses_cache_within_ttl(self) -> None:
        requests = _RecordingRequests()
        render_calls = []

        def renderer(*, sections, generated_at, asset_paths):
            render_calls.append((generated_at, len(sections), len(asset_paths)))
            return RenderedImage(content=b"png-1")

        now_box = {"value": 1000.0}
        with tempfile.TemporaryDirectory() as temp_dir:
            module = OWShopModule(
                requests=requests,
                cache_root=temp_dir,
                time_provider=lambda: now_box["value"],
                renderer=renderer,
            )

            first = await module.query_shop(render=True)
            second = await module.query_shop(render=True)

        self.assertEqual(first.image.content, b"png-1")
        self.assertEqual(second.image.content, b"png-1")
        self.assertEqual(requests.fetch_calls, len(SHOP_SECTION_SOURCES))
        self.assertEqual(len(render_calls), 1)

    async def test_service_refreshes_after_ttl_expiry(self) -> None:
        requests = _RecordingRequests()
        render_calls = []

        def renderer(*, sections, generated_at, asset_paths):
            render_calls.append(generated_at)
            return RenderedImage(content=f"png-{len(render_calls)}".encode("ascii"))

        now_box = {"value": 1000.0}
        with tempfile.TemporaryDirectory() as temp_dir:
            module = OWShopModule(
                requests=requests,
                cache_root=temp_dir,
                time_provider=lambda: now_box["value"],
                renderer=renderer,
            )
            first = await module.query_shop(render=True)
            now_box["value"] += 901.0
            second = await module.query_shop(render=True)

        self.assertEqual(first.image.content, b"png-1")
        self.assertEqual(second.image.content, b"png-2")
        self.assertEqual(requests.fetch_calls, len(SHOP_SECTION_SOURCES) * 2)
        self.assertEqual(len(render_calls), 2)

    async def test_partial_failure_still_returns_sections(self) -> None:
        requests = _RecordingRequests(fail_titles={SHOP_SECTION_SOURCES[1].title})
        with tempfile.TemporaryDirectory() as temp_dir:
            module = OWShopModule(requests=requests, cache_root=temp_dir, renderer=_fake_renderer)
            result = await module.query_shop(render=False)

        self.assertGreaterEqual(len(result.sections), 1)
        self.assertTrue(any(section.items for section in result.sections))

    async def test_all_failures_raise_module_error(self) -> None:
        requests = _RecordingRequests(fail_titles={source.title for source in SHOP_SECTION_SOURCES}, empty_titles=set())
        with tempfile.TemporaryDirectory() as temp_dir:
            module = OWShopModule(requests=requests, cache_root=temp_dir, renderer=_fake_renderer)
            with self.assertRaises(ModuleError) as ctx:
                await module.query_shop(render=False)

        self.assertEqual(ctx.exception.error, "ow_shop_unavailable")


class RenderSmokeTests(unittest.TestCase):
    def test_render_outputs_png_bytes(self) -> None:
        try:
            from PIL import Image
        except ModuleNotFoundError as exc:
            self.skipTest(str(exc))
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.png"
            Image.new("RGB", (640, 360), (80, 120, 200)).save(image_path, format="PNG")
            sections = [
                OWShopSection(
                    title="精选商品",
                    expires_text="1天2小时3分",
                    items=(
                        OWShopItem(
                            title="普通礼包",
                            description="传奇 | 礼包（3件物品）",
                            product_ids=(1, 2, 3),
                            price_raw=1900,
                            price_currency="XWC",
                            price_discount_percentage=0,
                            image_url="https://example.com/grid.png",
                        ),
                        OWShopItem(
                            title="超级礼包",
                            description="传奇 | 礼包（12件物品）",
                            product_ids=tuple(range(12)),
                            price_raw=3900,
                            price_currency="XVT",
                            price_discount_percentage=40,
                            image_url="https://example.com/hero.png",
                        ),
                    ),
                )
            ]
            rendered = render_ow_shop(
                sections=sections,
                generated_at="2026-04-29 12:34:56",
                asset_paths={
                    "https://example.com/grid.png": image_path,
                    "https://example.com/hero.png": image_path,
                },
            )

        self.assertTrue(rendered.content.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(rendered.media_type, "image/png")


class ServerBridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_bridge_returns_json_and_image(self) -> None:
        original_module = server_module.ow_shop_module
        server_module.ow_shop_module = _StubOWShopModule()
        try:
            service = server_module.OverstatsCoreService()
            payload = await service.handle_ow_shop({})
            image = await service.handle_ow_shop_image({})
        finally:
            server_module.ow_shop_module = original_module

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["sections"][0]["title"], "精选商品")
        self.assertEqual(image, b"stub-image")


class _RecordingRequests:
    def __init__(self, fail_titles=None, empty_titles=None) -> None:
        self.fetch_calls = 0
        self.fail_titles = set(fail_titles or set())
        self.empty_titles = (
            set(empty_titles)
            if empty_titles is not None
            else {source.title for source in SHOP_SECTION_SOURCES[1:]}
        )

    async def fetch_section(self, source) -> OWShopSection:
        self.fetch_calls += 1
        if source.title in self.fail_titles:
            raise RuntimeError(f"boom:{source.title}")
        if source.title in self.empty_titles:
            return OWShopSection(title=source.title, expires_text="", items=())
        return OWShopSection(
            title=source.title,
            expires_text="2天0小时0分",
            items=(
                OWShopItem(
                    title="测试商品",
                    description="传奇 | 礼包（2件物品）",
                    product_ids=(1, 2),
                    price_raw=1900,
                    price_currency="XWC",
                    price_discount_percentage=10,
                    image_url="https://example.com/item.png",
                ),
            ),
        )

    async def cache_images(self, image_urls, asset_dir):
        return {}


def _fake_renderer(*, sections, generated_at, asset_paths):
    return RenderedImage(content=b"fake-image")


class _StubOWShopModule:
    async def query_shop(self, *, render=False):
        section = OWShopSection(
            title="精选商品",
            expires_text="1天0小时0分",
            items=(
                OWShopItem(
                    title="测试商品",
                    description="传奇 | 礼包（2件物品）",
                    product_ids=(1, 2),
                    price_raw=1900,
                    price_currency="XWC",
                    price_discount_percentage=10,
                    image_url="https://example.com/item.png",
                ),
            ),
        )
        return OWShopOutput(
            generated_at="2026-04-29 12:34:56",
            cache_ttl_seconds=900,
            sections=(section,),
            image=RenderedImage(content=b"stub-image") if render else None,
        )
