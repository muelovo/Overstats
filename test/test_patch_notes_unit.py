from __future__ import annotations

import datetime as dt
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
    from overstats.src.modules.errors import ModuleError
    from overstats.src.modules.patch_notes.render import RenderedImage, render_patch_fallback, render_patch_notes
    from overstats.src.modules.patch_notes.requests import (
        PatchNotesRequests,
        build_sources_summary,
        choose_source,
        deserialize_patch_candidate,
        normalize_patch_kind,
    )
    from overstats.src.modules.patch_notes.service import PatchNotesModule, PatchNotesOutput
    import overstats.src.modules.patch_notes.requests as requests_module
    import overstats.src.server as server_module
except ModuleNotFoundError:
    from src.modules.errors import ModuleError
    from src.modules.patch_notes.render import RenderedImage, render_patch_fallback, render_patch_notes
    from src.modules.patch_notes.requests import (
        PatchNotesRequests,
        build_sources_summary,
        choose_source,
        deserialize_patch_candidate,
        normalize_patch_kind,
    )
    from src.modules.patch_notes.service import PatchNotesModule, PatchNotesOutput
    import src.modules.patch_notes.requests as requests_module
    import src.server as server_module


def _build_patch_html(title: str, date_text: str, *, extra_text: str = "") -> str:
    repeated_bullets = "".join(f"<li>{extra_text} #{index}</li>" for index in range(180)) if extra_text else ""
    return f"""
<div class="PatchNotes-patch PatchNotes-live">
  <h3 class="PatchNotes-patchTitle">{title}</h3>
  <div class="PatchNotes-date">{date_text}</div>
  <div class="PatchNotes-section">
    <h4 class="PatchNotes-sectionTitle">Hero Updates</h4>
    <div class="PatchNotes-sectionDescription">
      <p>General balance pass.</p>
    </div>
    <div class="PatchNotesHeroUpdate">
      <img class="PatchNotesHeroUpdate-icon" src="//example.com/tracer.png" />
      <div class="PatchNotesHeroUpdate-name">Tracer</div>
      <div class="PatchNotesHeroUpdate-generalUpdates">
        <li>Pulse Pistols damage increased by 1.</li>
      </div>
      <div class="PatchNotesAbilityUpdate">
        <img class="PatchNotesAbilityUpdate-icon" src="https://example.com/blink.png" />
        <div class="PatchNotesAbilityUpdate-name">Blink</div>
        <li>Cooldown lowered to 2.5 seconds.</li>
      </div>
      <div class="PatchNotesHeroUpdate-dev">
        <p>We want Tracer to stay proactive.</p>
      </div>
    </div>
  </div>
  <div class="PatchNotes-section">
    <h4 class="PatchNotes-sectionTitle">Map Updates</h4>
    <div class="PatchNotesMapUpdate">
      <div class="PatchNotesMapUpdate-name">Colosseo</div>
      <div class="PatchNotesMapUpdate-beforeAfterText">Before / After</div>
      <blz-image slot="before" src="//example.com/colosseo-before.png"></blz-image>
      <blz-image slot="after" src="https://example.com/colosseo-after.png"></blz-image>
      <p>Added more cover.</p>
      <li>Removed one flank path.</li>
    </div>
  </div>
  <div class="PatchNotes-section">
    <h4 class="PatchNotes-sectionTitle">General Updates</h4>
    <div class="PatchNotesGeneralUpdate">
      <div class="PatchNotesGeneralUpdate-title">Stadium</div>
      <div class="PatchNotesGeneralUpdate-description">
        <p>New crowd audio mix.</p>
        <li>Updated banners.</li>
        {repeated_bullets}
      </div>
      <div class="PatchNotesGeneralUpdate-dev">
        <p>Improves readability.</p>
      </div>
    </div>
  </div>
</div>
"""


def _candidate(
    *,
    source: str,
    title: str,
    date_text: str,
    bucket: str = "small",
    text: str = "English patch body",
) -> dict:
    if "18" in date_text:
        date_value = dt.date(2026, 4, 18)
    elif "17" in date_text:
        date_value = dt.date(2026, 4, 17)
    else:
        date_value = dt.date(2026, 4, 16)
    return {
        "source": source,
        "source_name": "外服" if source == "en" else "国服",
        "url": "https://example.com/patch",
        "index": 0,
        "title": title,
        "section_title": "Hero Updates",
        "date_text": date_text,
        "date": date_value,
        "length": len(text),
        "bucket": bucket,
        "bucket_name": "大更新" if bucket == "big" else "小更新",
        "text": text,
        "sections": [],
        "hero_updates": [],
    }


class RequestParsingTests(unittest.IsolatedAsyncioTestCase):
    async def test_scan_source_extracts_sections_and_normalizes_urls(self) -> None:
        request = _FixtureRequests(
            {
                "en": _build_patch_html(
                    "April 18, 2026 Retail Patch",
                    "April 18, 2026",
                    extra_text="Major systems update with lots of balance context.",
                )
            }
        )

        slots = await request.scan_patch_source("en", now_date=dt.date(2026, 4, 18))

        self.assertIsNotNone(slots["latest"])
        latest = slots["latest"]
        self.assertEqual(latest["bucket"], "big")
        self.assertEqual(latest["sections"][0]["hero_updates"][0]["name"], "Tracer")
        self.assertEqual(latest["sections"][0]["hero_updates"][0]["icon_url"], "https://example.com/tracer.png")
        self.assertEqual(latest["sections"][1]["map_updates"][0]["before_image_url"], "https://example.com/colosseo-before.png")
        self.assertEqual(latest["sections"][2]["general_updates"][0]["dev_note"], "Improves readability.")

    async def test_choose_source_prefers_newer_external_slot(self) -> None:
        cn_slots = {"latest": _candidate(source="cn", title="CN Patch", date_text="2026年4月17日")}
        en_slots = {"latest": _candidate(source="en", title="EN Patch", date_text="April 18, 2026")}

        chosen = choose_source(cn_slots, en_slots, slot_key="latest")

        self.assertEqual(chosen, "en")

    def test_normalize_patch_kind(self) -> None:
        self.assertEqual(normalize_patch_kind("small"), "small")
        self.assertEqual(normalize_patch_kind("大"), "big")
        self.assertEqual(normalize_patch_kind(""), "latest")
        with self.assertRaises(ValueError):
            normalize_patch_kind("weekly")

    def test_proxy_only_applies_to_external_source(self) -> None:
        request = PatchNotesRequests(use_international_proxy=True, international_proxy="http://127.0.0.1:7890")
        self.assertEqual(request.proxy_for_source("en"), "http://127.0.0.1:7890")
        self.assertEqual(request.proxy_for_source("cn"), "")

    def test_analysis_model_follows_base_url(self) -> None:
        original_google = getattr(requests_module.app_config, "ANALYSIS_GOOGLE_MODEL", None)
        original_deepseek = getattr(requests_module.app_config, "ANALYSIS_DEEPSEEK_MODEL", None)
        original_openai = getattr(requests_module.app_config, "ANALYSIS_OPENAI_MODEL", None)
        try:
            requests_module.app_config.ANALYSIS_GOOGLE_MODEL = "google-model"
            requests_module.app_config.ANALYSIS_DEEPSEEK_MODEL = "deepseek-model"
            requests_module.app_config.ANALYSIS_OPENAI_MODEL = "openai-model"
            self.assertEqual(requests_module._analysis_model_for_base_url("https://generativelanguage.googleapis.com/v1beta/openai"), "google-model")
            self.assertEqual(requests_module._analysis_model_for_base_url("https://api.deepseek.com/v1"), "deepseek-model")
            self.assertEqual(requests_module._analysis_model_for_base_url("https://api.openai.com/v1"), "openai-model")
        finally:
            requests_module.app_config.ANALYSIS_GOOGLE_MODEL = original_google
            requests_module.app_config.ANALYSIS_DEEPSEEK_MODEL = original_deepseek
            requests_module.app_config.ANALYSIS_OPENAI_MODEL = original_openai


class PatchNotesModuleTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_uses_cached_translated_bundle(self) -> None:
        requests = _RecordingPatchRequests()
        render_calls = []

        def renderer(candidate, *, summary_text, asset_paths):
            render_calls.append((candidate["title"], summary_text, len(asset_paths)))
            return RenderedImage(content=f"png-{len(render_calls)}".encode("ascii"))

        with tempfile.TemporaryDirectory() as temp_dir:
            module = PatchNotesModule(
                requests=requests,
                cache_root=temp_dir,
                renderer=renderer,
            )

            first = await module.query_patch_notes(patch_kind="latest", render=True)
            second = await module.query_patch_notes(patch_kind="latest", render=True)

            cache_files = sorted(path.name for path in Path(temp_dir).glob("*") if path.is_file())

        self.assertEqual(first.image.content, b"png-1")
        self.assertEqual(second.image.content, b"png-1")
        self.assertEqual(requests.translate_calls, 1)
        self.assertEqual(len(render_calls), 1)
        self.assertTrue(any(name.endswith(".json") for name in cache_files))
        self.assertTrue(any(name.endswith(".png") for name in cache_files))

    async def test_service_does_not_persist_cn_bundle(self) -> None:
        requests = _RecordingPatchRequests(chosen_source="cn")
        with tempfile.TemporaryDirectory() as temp_dir:
            module = PatchNotesModule(
                requests=requests,
                cache_root=temp_dir,
                renderer=lambda candidate, *, summary_text, asset_paths: RenderedImage(content=b"cn-image"),
            )
            result = await module.query_patch_notes(patch_kind="latest", render=True)
            cache_files = sorted(path.name for path in Path(temp_dir).glob("*") if path.is_file())

        self.assertEqual(result.source, "cn")
        self.assertEqual(cache_files, [])

    async def test_translation_failure_falls_back_to_untranslated_candidate(self) -> None:
        requests = _RecordingPatchRequests(raise_on_translate=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            module = PatchNotesModule(
                requests=requests,
                cache_root=temp_dir,
                renderer=lambda candidate, *, summary_text, asset_paths: RenderedImage(content=b"fallback"),
            )
            result = await module.query_patch_notes(patch_kind="latest", render=False)

        self.assertFalse(result.translated)
        self.assertEqual(result.selected["title"], "April 18, 2026 Retail Patch")

    async def test_missing_sources_raise_module_error(self) -> None:
        requests = _RecordingPatchRequests(empty=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            module = PatchNotesModule(requests=requests, cache_root=temp_dir)
            with self.assertRaises(ModuleError) as ctx:
                await module.query_patch_notes(patch_kind="latest", render=False)

        self.assertEqual(ctx.exception.error, "patch_notes_unavailable")


class RenderSmokeTests(unittest.TestCase):
    def test_render_outputs_png_bytes(self) -> None:
        try:
            from PIL import Image
        except ModuleNotFoundError as exc:
            self.skipTest(str(exc))
            return

        candidate = deserialize_patch_candidate(
            {
                "source": "en",
                "source_name": "外服",
                "url": "https://example.com/patch",
                "index": 0,
                "title": "April 18, 2026 Retail Patch",
                "section_title": "Hero Updates",
                "date_text": "April 18, 2026",
                "date": "2026-04-18",
                "length": 3200,
                "bucket": "big",
                "bucket_name": "大更新",
                "text": "Patch body",
                "sections": [
                    {
                        "type": "hero",
                        "title": "Hero Updates",
                        "intro": ["General balance pass."],
                        "hero_updates": [
                            {
                                "name": "猎空",
                                "icon_url": "https://example.com/tracer.png",
                                "dev_note": "希望猎空更主动。",
                                "general_changes": ["脉冲双枪伤害提高。"],
                                "abilities": [
                                    {
                                        "name": "闪现",
                                        "icon_url": "https://example.com/blink.png",
                                        "changes": ["冷却时间缩短。"],
                                    }
                                ],
                                "group_title": "英雄改动",
                            }
                        ],
                        "map_updates": [],
                        "general_updates": [],
                    },
                    {
                        "type": "map",
                        "title": "Map Updates",
                        "intro": [],
                        "hero_updates": [],
                        "map_updates": [
                            {
                                "name": "斗兽场",
                                "comparison_label": "Before / After",
                                "paragraphs": ["增加了掩体。"],
                                "bullets": ["移除一条侧路。"],
                                "before_image_url": "https://example.com/before.png",
                                "after_image_url": "https://example.com/after.png",
                            }
                        ],
                        "general_updates": [],
                    },
                    {
                        "type": "general",
                        "title": "General Updates",
                        "intro": [],
                        "hero_updates": [],
                        "map_updates": [],
                        "general_updates": [
                            {
                                "title": "Stadium",
                                "paragraphs": ["新的观众音效。"],
                                "bullets": ["横幅更新。"],
                                "dev_note": "提升可读性。",
                            }
                        ],
                    },
                ],
                "hero_updates": [],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.png"
            Image.new("RGB", (640, 360), (80, 120, 200)).save(image_path, format="PNG")
            rendered = render_patch_notes(
                candidate,
                summary_text="国服最新：2026-04-17\n外服最新：2026-04-18",
                asset_paths={
                    "https://example.com/tracer.png": image_path,
                    "https://example.com/blink.png": image_path,
                    "https://example.com/before.png": image_path,
                    "https://example.com/after.png": image_path,
                },
            )
            fallback = render_patch_fallback(candidate, summary_text="Fallback summary")

        self.assertTrue(rendered.content.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertTrue(fallback.content.startswith(b"\x89PNG\r\n\x1a\n"))


class ServerBridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_bridge_returns_json_and_image(self) -> None:
        original_module = server_module.patch_notes_module
        server_module.patch_notes_module = _StubPatchNotesModule()
        try:
            service = server_module.OverstatsCoreService()
            payload = await service.handle_patch_notes({})
            image = await service.handle_patch_notes_image({"patch_kind": "small"})
        finally:
            server_module.patch_notes_module = original_module

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["source"], "en")
        self.assertEqual(payload["selected"]["title"], "April 18, 2026 Retail Patch")
        self.assertEqual(image, b"stub-image")


class _FixtureRequests(PatchNotesRequests):
    def __init__(self, pages: dict[str, str]) -> None:
        super().__init__(use_international_proxy=False)
        self.pages = dict(pages)

    async def fetch_patch_page_html(self, url: str, source_key: str) -> str:
        if source_key not in self.pages:
            raise RuntimeError(f"missing fixture for {source_key}")
        return self.pages[source_key]


class _RecordingPatchRequests:
    def __init__(self, *, chosen_source: str = "en", raise_on_translate: bool = False, empty: bool = False) -> None:
        self.chosen_source = chosen_source
        self.raise_on_translate = raise_on_translate
        self.empty = empty
        self.translate_calls = 0
        self.scan_calls = 0
        self.cache_image_calls = 0

    async def scan_sources(self, *, now_date=None):
        self.scan_calls += 1
        if self.empty:
            empty_slots = {"latest": None, "small": None, "big": None}
            return empty_slots, empty_slots
        cn_candidate = _candidate(source="cn", title="2026年4月17日补丁说明", date_text="2026年4月17日")
        en_date_text = "April 18, 2026" if self.chosen_source == "en" else "April 16, 2026"
        en_candidate = _candidate(source="en", title="April 18, 2026 Retail Patch", date_text=en_date_text)
        return (
            {"latest": cn_candidate, "small": cn_candidate, "big": cn_candidate},
            {"latest": en_candidate, "small": en_candidate, "big": en_candidate},
        )

    async def translate_patch_candidate(self, candidate):
        self.translate_calls += 1
        if self.raise_on_translate:
            raise RuntimeError("translation failed")
        translated = dict(candidate)
        translated["title"] = "2026年4月18日零售版补丁"
        translated["text"] = "已翻译补丁正文"
        return translated, True

    async def cache_images(self, image_urls, asset_dir, *, use_proxy=False, max_concurrency=6):
        self.cache_image_calls += 1
        return {}


class _StubPatchNotesModule:
    async def query_patch_notes(self, *, patch_kind=None, render=False):
        return PatchNotesOutput(
            requested_kind=str(patch_kind or "latest") or "latest",
            selected_kind=str(patch_kind or "latest") or "latest",
            source="en",
            source_name="外服",
            translated=True,
            summary="外服最新：2026-04-18",
            selected={
                "source": "en",
                "source_name": "外服",
                "title": "April 18, 2026 Retail Patch",
                "section_title": "Hero Updates",
                "date_text": "April 18, 2026",
                "date": dt.date(2026, 4, 18),
                "bucket": "small",
                "bucket_name": "小更新",
                "text": "Patch body",
                "sections": [],
                "hero_updates": [],
            },
            sources=build_sources_summary(
                {"latest": _candidate(source="cn", title="cn", date_text="2026年4月17日"), "small": None, "big": None},
                {"latest": _candidate(source="en", title="en", date_text="April 18, 2026"), "small": None, "big": None},
            ),
            image=RenderedImage(content=b"stub-image") if render else None,
        )
