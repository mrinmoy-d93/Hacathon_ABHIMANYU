"""OpenAI GPT-4o summaries and alert message generation."""
from __future__ import annotations

SYSTEM_PROMPT_VERSION = "khojo-summary-v1"


async def case_summary(case: dict) -> str:
    raise NotImplementedError("Wire up OpenAI call in implementation phase")


async def community_alert(case: dict, match: dict) -> str:
    raise NotImplementedError("Wire up OpenAI call in implementation phase")
