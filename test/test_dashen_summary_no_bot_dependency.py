from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_PATH = REPO_ROOT / "src" / "modules" / "dashen_summary" / "engine.py"
RUNTIME_PATH = REPO_ROOT / "src" / "modules" / "dashen_summary" / "runtime" / "season_conclusion.py"


class DashenSummaryNoBotDependencyTests(unittest.TestCase):
    def test_engine_source_has_no_forbidden_bot_marker(self) -> None:
        forbidden = "".join(["hos", "hino"])
        source = ENGINE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(forbidden, source)

    def test_runtime_source_has_no_forbidden_bot_marker(self) -> None:
        forbidden = "".join(["hos", "hino"])
        source = RUNTIME_PATH.read_text(encoding="utf-8")
        self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
