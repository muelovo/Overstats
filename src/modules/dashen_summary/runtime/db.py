from __future__ import annotations

from typing import Any, Dict, List, Optional


class IDPoolDB:
    """Local no-op database adapter for standalone overstats summary rendering."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def get_all_rank(self) -> List[Dict[str, Any]]:
        return []

    def get_group_titles(self, bnet_id: str) -> List[Dict[str, Any]]:
        return []

    def get_statmap_summary(
        self,
        hero_guid: str,
        statmap_names: Optional[List[str]] = None,
        rank_scores: Optional[List[int]] = None,
        ratio_statmap_names: Optional[List[str]] = None,
        group_by_rank: bool = True,
    ) -> Dict[str, Any]:
        return {}

    def get_entry_ds_exact_ci_one(self, battletag: str, battlenum: Optional[int] = None) -> Optional[Dict[str, Any]]:
        return None

    def get_entry_ds(self, *args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        return []

    def get_all_entries_ds2(self) -> List[Dict[str, Any]]:
        return []

    def __getattr__(self, name: str) -> Any:
        def _noop(*args: Any, **kwargs: Any) -> Any:
            if name.startswith("get_"):
                return []
            return None

        return _noop
