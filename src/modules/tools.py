from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ModuleEntry:
    name: str
    import_path: str
    description: str


MODULE_REGISTRY: Dict[str, ModuleEntry] = {}


def register_module(name: str, import_path: str, description: str = "") -> ModuleEntry:
    entry = ModuleEntry(name=name, import_path=import_path, description=description)
    MODULE_REGISTRY[name] = entry
    return entry


def get_module_registry() -> Dict[str, ModuleEntry]:
    return dict(MODULE_REGISTRY)


register_module(
    "query_tool",
    "overstats.src.modules.query_tool",
    "Overwatch query tool config loader and refresher.",
)

register_module(
    "bnet_search",
    "overstats.src.modules.bnet_search",
    "BattleTag search and customer token resolving.",
)

register_module(
    "dashen_match",
    "overstats.src.modules.dashen_match",
    "Dashen match list and detail data orchestration.",
)

register_module(
    "dashen_profile",
    "overstats.src.modules.dashen_profile",
    "Dashen profile card plus sport and leisure count data orchestration.",
)

register_module(
    "dashen_summary",
    "overstats.src.modules.dashen_summary",
    "Dashen daily and periodic summary worker bridge.",
)

register_module(
    "dashen_rank_history",
    "overstats.src.modules.dashen_rank_history",
    "Dashen historical competitive and stadium rank timeline renderer.",
)
