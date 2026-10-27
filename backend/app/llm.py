"""LLM adapter (decision D4): swappable backend, deterministic demo by default.

``DemoLLM`` is offline + zero-cost and always flags output advisory.
``OllamaLLM`` / ``OpenRouterLLM`` upgrade in place via ``settings.llm_backend``.
All produced content carries ``advisory=True`` so callers render the disclaimer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.config import settings


@dataclass
class ComposeResult:
    subject: str
    body: str
    lang: str = "en"
    advisory: bool = True
    backend: str = "demo"
    notes: list[str] = field(default_factory=list)


class LLMBackend(Protocol):
    name: str

    def compose_notice(self, *, context: dict, lang: str = "en") -> ComposeResult:
        ...


class DemoLLM:
    """Deterministic template composer. No network, no API key, reproducible.

    Used in CI/tests and as the zero-cost default. Mirrors what a live LLM would
    return so the API surface is identical."""
    name = "demo"

    @staticmethod
    def _safe_format(template: str, ctx: dict) -> str:
        """Format known ``{key}`` / ``{key:spec}`` placeholders; leave unknown
        ones in place (no KeyError, no format-code crashes)."""
        import re
        def repl(m: "re.Match") -> str:
            name, spec = m.group(1), m.group(2) or ""
            if name in ctx:
                try:
                    return format(ctx[name], spec) if spec else str(ctx[name])
                except (ValueError, TypeError):
                    return m.group(0)
            return m.group(0)
        return re.sub(r"\{(\w+)(?::([^}]*))?\}", repl, template)

    TEMPLATES = {
        "at_risk": (
            "Attention: academic support plan",
            "{student} has been flagged by our at-risk model (confidence {score:.0%}). "
            "Top factors: {reasons}. Suggested action: schedule a parent-teacher meet "
            "and a support plan within 2 weeks. This is advisory; please verify against "
            "class records.",
        ),
        "fee_default": (
            "Fee default notice",
            "{student}'s account shows {dues:,.0f} paise outstanding across {bills} bills. "
            "Suggested communication: two reminders 10 days apart, then a call. "
            "Advisory; confirm balances with the ledger.",
        ),
        "result_letter": (
            "Term result letter",
            "Dear {guardian}, {student} completed {exam} with {pct:.1f}% "
            "in division {division}. Advisory summary generated; see full report for detail.",
        ),
    }

    def compose_notice(self, *, context: dict, lang: str = "en") -> ComposeResult:
        kind = context.get("kind", "result_letter")
        subject, template = self.TEMPLATES.get(kind, self.TEMPLATES["result_letter"])
        # safe formatting: unknown placeholders are left in place rather than raising
        body = self._safe_format(template, context) if "{" in template else template
        return ComposeResult(subject=subject, body=body, lang=lang,
                              advisory=True, backend=self.name,
                              notes=["deterministic demo template; no LLM called"])


class OllamaLLM:
    """Local Ollama (optional). Requires a running Ollama server + model."""
    name = "ollama"

    def __init__(self):
        import httpx
        self._http = httpx.Client(base_url=settings.ollama_base_url, timeout=60)
        self._model = "llama3"

    def compose_notice(self, *, context: dict, lang: str = "en") -> ComposeResult:
        prompt = ("You are a school administrator assistant. Draft a short, factual, "
                  "advisory notice in English using this context: " + str(context))
        r = self._http.post("/api/generate", json={"model": self._model, "prompt": prompt})
        text = r.json().get("response", "")
        return ComposeResult(subject="Advisory notice", body=text, lang=lang,
                              advisory=True, backend=self.name)


class OpenRouterLLM:
    name = "openrouter"

    def __init__(self):
        import httpx
        self._http = httpx.Client(timeout=60)

    def compose_notice(self, *, context: dict, lang: str = "en") -> ComposeResult:
        r = self._http.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={"model": settings.openrouter_model,
                  "messages": [{"role": "user", "content": str(context)}]})
        text = r.json()["choices"][0]["message"]["content"]
        return ComposeResult(subject="Advisory notice", body=text, lang=lang,
                              advisory=True, backend=self.name)


def get_llm() -> LLMBackend:
    b = settings.llm_backend.lower()
    if b == "ollama":
        return OllamaLLM()
    if b == "openrouter":
        return OpenRouterLLM()
    return DemoLLM()
