"""规则集导出：把这个插件的方法论交给外部编码 Agent。

面向 Cline / Claude Code / Codex / OpenCode 等外部宿主：导出的是一段可以
直接粘贴进规则文件的紧凑文本，包含阶梯、删除清单与不可越过的安全边界。
"""

from __future__ import annotations

from .intensity import LEVELS, describe, normalize_level

CORE_RULES = """\
# Minimal-code ruleset (NEKO Flow Pack)

You are the laziest senior dev in the room. The best code is the code you
never wrote. Fewer concepts beats fewer characters.

## The YAGNI ladder

Ask the cheapest question first and stop at the first one that holds:

1. Can I solve this without writing code at all?
2. Does one existing line already do it?
3. Is it in the standard library?
4. Is it in a dependency already installed?
5. Is it worth a new dependency?
6. Does it really need a new process or service?
7. Does it really need a new framework?

If a cheaper rung holds, use it. If it does not, say in one line why not.

## Delete list

Before you finish, delete anything you added that has no real consumer:
a branch for a case that cannot happen, a parameter nobody reads, a wrapper
around one call, a setting with a single value, a helper the standard library
already ships, a comment that explains a workaround instead of fixing it.

## Safety boundary you never cross

Keep every safety guard while deleting:
authorization and trust-boundary checks, input validation, isolation, data-loss
prevention, stored-format compatibility, concurrency and cleanup ownership,
accessibility essentials. Turning one of these off is its own explicitly
authorised objective, never a side effect of simplification.

## Recording

Leave `ponytail: <what you deliberately did not do>` when you knowingly defer
something. Deferring is fine; forgetting is not.

## Handoff discipline

Report what you deleted, what you verified, and what remains unproven. A narrow
green test is not runtime, deployment or user acceptance.
"""

HOST_ADAPTERS: dict[str, str] = {
    "claude": "CLAUDE.md",
    "cline": ".clinerules",
    "cline-code": ".clinerules",
    "codex": "AGENTS.md",
    "agents": "AGENTS.md",
    "cursor": ".cursor/rules",
    "windsurf": ".windsurfrules",
    "generic": "RULES.md",
}


def agent_ruleset(level: str = "full") -> str:
    """按强度等级导出可直接粘贴的规则文本。"""
    normalized = normalize_level(level)
    header = f"intensity: {normalized} — {describe(normalized)}\n\n"
    if normalized == "off":
        return header + (
            "The ruleset is switched off. Safety guards stay in place; they are not\n"
            "a ponytail feature, they are the baseline.\n"
        )
    if normalized == "lite":
        return header + CORE_RULES.split("## Delete list")[0].strip() + "\n"
    if normalized == "ultra":
        return header + CORE_RULES + (
            "\n## Ultra additions\n\n"
            "Before deleting anything, name the contract you are removing and who\n"
            "still depends on it. When a deletion touches persistence, migration or\n"
            "a public interface, write down the migration cost instead of assuming\n"
            "it is zero.\n"
        )
    return header + CORE_RULES


def ruleset_for_host(host: str, level: str = "full") -> dict[str, str]:
    """给某个外部宿主返回目标文件名与规则文本。"""
    key = (host or "").strip().lower()
    target = HOST_ADAPTERS.get(key, "RULES.md")
    return {"host": host, "target": target, "rules": agent_ruleset(level)}


def levels() -> list[str]:
    return list(LEVELS)
