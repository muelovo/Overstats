import datetime as dt
import unittest
from unittest import mock

from src.modules.ow_hero_leaderboard import service


class OWHeroLeaderboardTimezoneFallbackTest(unittest.TestCase):
    def test_load_beijing_timezone_falls_back_when_tzdata_is_missing(self) -> None:
        with mock.patch.object(
            service,
            "ZoneInfo",
            side_effect=service.ZoneInfoNotFoundError("Asia/Shanghai"),
        ):
            timezone = service._load_beijing_timezone()

        sample_time = dt.datetime(2026, 5, 29, 12, 0, 0)
        self.assertEqual(timezone.utcoffset(sample_time), dt.timedelta(hours=8))
        self.assertEqual(timezone.tzname(sample_time), "Asia/Shanghai")


if __name__ == "__main__":
    unittest.main()
