"""Rule base class + auto-registry."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, ClassVar, Literal

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules._issue import Issue, Severity

REGISTRY: dict[str, type["Rule"]] = {}


class Rule:
    """Base class for all SEO detection rules.

    Each rule is a self-contained Python file in
    `src/crawlforge/rules/<category>/<rule_id>.py` decorated with
    `@register_rule`.

    Subclasses MUST set the class-level metadata fields and implement
    `check`. See `docs/RULES_API.md` for the full contract.
    """

    id: ClassVar[str] = ""
    name: ClassVar[str] = ""
    category: ClassVar[str] = ""
    severity: ClassVar[Severity] = "info"
    description: ClassVar[str] = ""
    fix_guidance: ClassVar[str] = ""
    references: ClassVar[list[str]] = []
    enabled_by_default: ClassVar[bool] = True
    requires_rendered_html: ClassVar[bool] = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        raise NotImplementedError

    @classmethod
    def metadata(cls) -> dict[str, Any]:
        return {
            "id": cls.id,
            "name": cls.name,
            "category": cls.category,
            "severity": cls.severity,
            "description": cls.description,
            "fix_guidance": cls.fix_guidance,
            "references": list(cls.references),
            "enabled_by_default": cls.enabled_by_default,
            "requires_rendered_html": cls.requires_rendered_html,
        }


def register_rule(cls: type[Rule]) -> type[Rule]:
    """Class decorator that registers a Rule in the global REGISTRY."""
    if not cls.id:
        raise ValueError(f"{cls.__name__} must set class attribute `id`.")
    if not cls.name:
        raise ValueError(f"{cls.__name__} must set class attribute `name`.")
    if not cls.category:
        raise ValueError(f"{cls.__name__} must set class attribute `category`.")
    if cls.severity not in ("critical", "warning", "info"):
        raise ValueError(
            f"{cls.__name__}.severity must be 'critical', 'warning' or 'info', "
            f"got {cls.severity!r}."
        )
    if cls.id in REGISTRY:
        existing = REGISTRY[cls.id].__module__
        raise ValueError(
            f"Duplicate rule id {cls.id!r} (already registered by {existing}, "
            f"now attempted by {cls.__module__})."
        )
    REGISTRY[cls.id] = cls
    return cls


def discover_rules() -> dict[str, type[Rule]]:
    """Force-import all rule modules so @register_rule fires."""
    import importlib
    import pkgutil

    import modules.seo_rules.rules as pkg

    for mod in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + "."):
        if mod.name.endswith("._registry") or mod.name.endswith("._issue"):
            continue
        importlib.import_module(mod.name)

    return dict(REGISTRY)
