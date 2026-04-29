from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
PARENT_DIR = REPO_ROOT.parent
for candidate in (PARENT_DIR, REPO_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from overstats.src.constants import backgrounds as backgrounds_module
    from overstats.src.modules.ow_shop.render import render_ow_shop
    from overstats.src.modules.ow_shop.requests import OWShopItem, OWShopSection
    import overstats.src.modules.ow_shop.render as ow_shop_render_module
    import overstats.src.modules.patch_notes.render as patch_notes_render_module
except ModuleNotFoundError:
    from src.constants import backgrounds as backgrounds_module
    from src.modules.ow_shop.render import render_ow_shop
    from src.modules.ow_shop.requests import OWShopItem, OWShopSection
    import src.modules.ow_shop.render as ow_shop_render_module
    import src.modules.patch_notes.render as patch_notes_render_module


try:
    from PIL import Image
except ModuleNotFoundError:
    Image = None


@unittest.skipIf(Image is None, "Pillow not installed")
class BackgroundHelperTests(unittest.TestCase):
    def test_list_map_background_paths_filters_suffixes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            (temp_dir / "notes.txt").write_text("ignore", encoding="utf-8")
            Image.new("RGB", (8, 8), (255, 0, 0)).save(temp_dir / "map-b.png")
            Image.new("RGB", (8, 8), (0, 255, 0)).save(temp_dir / "map-a.jpg")

            paths = backgrounds_module.list_map_background_paths(temp_dir)

            self.assertEqual([path.name for path in paths], ["map-a.jpg", "map-b.png"])

    def test_build_random_map_background_returns_resized_image(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            image_path = temp_dir / "sample.png"
            Image.new("RGB", (40, 20), (12, 34, 56)).save(image_path)

            background = backgrounds_module.build_random_map_background(
                (120, 80),
                directory=temp_dir,
                blur_radius=0,
                overlay=None,
                brightness=1.0,
                color=1.0,
            )

            self.assertIsNotNone(background)
            self.assertEqual(background.size, (120, 80))


@unittest.skipIf(Image is None, "Pillow not installed")
class ModuleBackgroundPreferenceTests(unittest.TestCase):
    def test_ow_shop_render_uses_shared_map_background_when_available(self) -> None:
        original_builder = ow_shop_render_module.build_random_map_background
        marker_color = (123, 45, 67, 255)

        def fake_builder(size, **_: object):
            return Image.new("RGBA", size, marker_color)

        ow_shop_render_module.build_random_map_background = fake_builder
        try:
            rendered = render_ow_shop(
                [
                    OWShopSection(
                        title="精选商品",
                        expires_text="2天",
                        items=(
                            OWShopItem(
                                title="测试商品",
                                description="测试描述",
                                product_ids=(1,),
                                price_raw=1000,
                                price_currency="XWC",
                                price_discount_percentage=0,
                                image_url="",
                            ),
                        ),
                    ),
                ],
                generated_at="2026-04-29 12:00",
                asset_paths={},
            )
        finally:
            ow_shop_render_module.build_random_map_background = original_builder

        with Image.open(BytesIO(rendered.content)) as output_image:
            pixel = output_image.convert("RGBA").getpixel((0, 0))
        self.assertEqual(pixel, marker_color)

    def test_patch_notes_background_changes_when_shared_map_background_exists(self) -> None:
        original_builder = patch_notes_render_module.build_random_map_background

        patch_notes_render_module.build_random_map_background = lambda size, **_: None
        try:
            fallback_background = patch_notes_render_module._build_background(220, 140).copy()
        finally:
            patch_notes_render_module.build_random_map_background = original_builder

        patch_notes_render_module.build_random_map_background = lambda size, **_: Image.new("RGBA", size, (20, 90, 140, 255))
        try:
            random_background = patch_notes_render_module._build_background(220, 140).copy()
        finally:
            patch_notes_render_module.build_random_map_background = original_builder

        self.assertNotEqual(fallback_background.tobytes(), random_background.tobytes())


if __name__ == "__main__":
    unittest.main()
