"""SEO rule catalog â€” auto-discovery via @register_rule decorator."""

from modules.seo_rules.rules._registry import REGISTRY, Rule, register_rule

__all__ = ["REGISTRY", "Rule", "register_rule"]
