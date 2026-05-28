from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.http_server.registry import get_http_ui_bootstrap_payload
from src.modules.ow_guess import catalog


class OWGuessAssetRootResolutionTest(unittest.TestCase):
    def test_pick_default_asset_root_prefers_first_existing_candidate(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            primary = base / "ow_guess_assets"
            legacy = base / "legacy_ow_guess_assets"
            primary.mkdir()
            legacy.mkdir()

            self.assertEqual(catalog._pick_default_asset_root((primary, legacy)), primary.resolve())

    def test_pick_default_asset_root_falls_back_to_first_candidate(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            primary = base / "ow_guess_assets"
            legacy = base / "legacy_ow_guess_assets"

            self.assertEqual(catalog._pick_default_asset_root((primary, legacy)), primary.resolve())

    def test_resolve_asset_root_uses_default_picker_for_legacy_default_value(self) -> None:
        sentinel = Path("C:/tmp/ow_guess_assets")
        with mock.patch.object(catalog, "_pick_default_asset_root", return_value=sentinel):
            self.assertEqual(catalog._resolve_asset_root("../ow_guess_assets"), sentinel)

    def test_resolve_asset_root_keeps_custom_relative_path(self) -> None:
        expected = (catalog.PROJECT_ROOT / "custom/assets").resolve()
        self.assertEqual(catalog._resolve_asset_root("custom/assets"), expected)


class OWGuessHTTPUIBootstrapTest(unittest.TestCase):
    def test_http_ui_bootstrap_contains_ow_guess_module(self) -> None:
        payload = get_http_ui_bootstrap_payload()
        modules = payload.get("modules") or []
        ow_guess_module = next((item for item in modules if item.get("id") == "ow-guess"), None)

        self.assertIsNotNone(ow_guess_module)
        self.assertEqual(ow_guess_module.get("json_endpoint"), "/api/v2/ow-guess/replies")
        self.assertFalse(ow_guess_module.get("requires_target"))

        fields = ow_guess_module.get("fields") or []
        question_type_field = next((item for item in fields if item.get("payload_key") == "question_type"), None)

        self.assertIsNotNone(question_type_field)
        self.assertEqual(question_type_field.get("control_type"), "select")
        self.assertTrue(any(option.get("value") == "hero_icon" for option in question_type_field.get("options") or []))


if __name__ == "__main__":
    unittest.main()
