"""ClaudeClient — Anthropic SDK ile Stage 2 (Haiku) + Stage 3 (Opus) implementation.

Özellikler:
- Tool calling structured output (no JSON parsing kabusları)
- Prompt caching (skill content cache'lenir, %90 maliyet düşüşü)
- Cost tracking (input + output + cache token bazlı)
- Retry: tenacity ile exponential backoff
- Two tiers: ScreenClient (Haiku 4.5), DeepClient (Opus 4.7)
"""
from __future__ import annotations

from typing import Any

from anthropic import Anthropic, APIError
from anthropic.types import Message
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from finllm.config.settings import settings
from finllm.llm.base import (
    DeepAnalysis,
    LLMClient,
    PriceScenarioOutput,
    ScreenVerdict,
)
from finllm.skills import load_skill
from finllm.utils.logging import logger


# Pricing per million tokens (USD) — Mayıs 2026 itibariyle güncel oranlar
PRICING = {
    "claude-haiku-4-5-20251001": {
        "input": 1.00,
        "output": 5.00,
        "cache_write": 1.25,
        "cache_read": 0.10,
    },
    "claude-sonnet-4-6": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-opus-4-7": {
        "input": 15.00,
        "output": 75.00,
        "cache_write": 18.75,
        "cache_read": 1.50,
    },
}


# ---- Tool schemas (structured output) ----
SCREEN_TOOL = {
    "name": "produce_screen",
    "description": "Output the screen verdict and rationale for one ticker.",
    "input_schema": {
        "type": "object",
        "required": ["verdict", "rationale"],
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["strong", "potential", "skip"],
                "description": "Stage 3'e geçirilecek mi (strong/potential) yoksa skip mi?",
            },
            "rationale": {
                "type": "string",
                "description": "1-2 cümle gerekçe. En güçlü faktörü cite et (confluence, setup, regime).",
                "maxLength": 280,
            },
        },
    },
}

DEEP_TOOL = {
    "name": "produce_analysis",
    "description": "Output the structured deep analysis for one ticker. All decisions go through this tool.",
    "input_schema": {
        "type": "object",
        "required": ["signal", "confidence", "rationale_full"],
        "properties": {
            "signal": {
                "type": "string",
                "enum": ["GUCLU_AL", "AL", "IZLE", "TUT", "KISMI_SAT", "SAT", "ACIL_SAT"],
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "expected_return_pct": {
                "type": ["number", "null"],
                "description": "Probability-weighted return; null if IZLE/TUT/SAT",
            },
            "time_horizon_days": {
                "type": ["integer", "null"],
                "minimum": 5,
                "maximum": 10,
            },
            "entry_zone_low": {"type": ["number", "null"]},
            "entry_zone_high": {"type": ["number", "null"]},
            "stop_loss": {"type": ["number", "null"]},
            "scenarios": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": ["label", "target_price", "probability", "expected_return_pct"],
                    "properties": {
                        "label": {"type": "string", "enum": ["base", "bull", "bear"]},
                        "target_price": {"type": "number"},
                        "probability": {"type": "number", "minimum": 0, "maximum": 1},
                        "expected_return_pct": {"type": "number"},
                    },
                },
            },
            "rationale_trend": {"type": "string", "maxLength": 400},
            "rationale_formation": {"type": "string", "maxLength": 400},
            "rationale_volume": {"type": "string", "maxLength": 400},
            "rationale_news": {"type": "string", "maxLength": 400},
            "rationale_fibonacci": {"type": "string", "maxLength": 600},
            "rationale_risks": {
                "type": "array",
                "maxItems": 6,
                "items": {"type": "string", "maxLength": 200},
            },
            "rationale_full": {
                "type": "string",
                "description": "3-4 paragraphs: detailed 10-day price action scenario with Fibonacci levels, support/resistance targets, base/bull/bear narratives. Readable analyst-report style.",
                "maxLength": 4000,
            },
            "warning_flags": {
                "type": "array",
                "maxItems": 8,
                "items": {"type": "string"},
            },
            "unsourced_flag": {"type": "boolean"},
        },
    },
}


def _calculate_cost(model: str, usage: Any) -> float:
    """Token usage'dan USD maliyet hesapla. Cache hit fields varsa onları kullan."""
    pricing = PRICING.get(model)
    if not pricing:
        return 0.0

    input_tok = getattr(usage, "input_tokens", 0)
    output_tok = getattr(usage, "output_tokens", 0)
    cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

    # Effective input = total input - cached portion
    fresh_input = max(0, input_tok - cache_read - cache_create)

    cost = (
        (fresh_input / 1_000_000) * pricing["input"]
        + (output_tok / 1_000_000) * pricing["output"]
        + (cache_create / 1_000_000) * pricing["cache_write"]
        + (cache_read / 1_000_000) * pricing["cache_read"]
    )
    return cost


def _extract_tool_input(response: Message, tool_name: str) -> dict | None:
    """Response'dan tool_use bloğunun input'unu çıkar."""
    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input
    return None


class _BaseClaudeClient:
    """Ortak retry + Anthropic SDK setup."""

    def __init__(self, api_key: str | None = None):
        key = api_key or settings.anthropic_api_key
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY .env'de yok")
        self._client = Anthropic(api_key=key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(APIError),
        reraise=True,
    )
    def _call(
        self,
        model: str,
        system: list[dict],
        user_content: str,
        tools: list[dict],
        tool_choice: dict | None = None,
        max_tokens: int = 1024,
    ) -> Message:
        # NOT: Opus 4.7+ modelleri `temperature` parametresini kabul etmiyor
        # ("deprecated for this model"). Default davranışa bırakıyoruz.
        return self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            tool_choice=tool_choice or {"type": "any"},
            messages=[{"role": "user", "content": user_content}],
        )


class ClaudeScreenClient(_BaseClaudeClient, LLMClient):
    """Stage 2 — Haiku 4.5 ile cheap screening.

    Maliyet: ~$0.001-0.002 per ticker (cache hit ile $0.0002).
    """

    name = "claude-haiku-4-5-20251001"

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key=api_key)
        self._system_skill = load_skill("cheap-screener")
        self.cost_per_1k_input = PRICING[self.name]["input"] / 1000
        self.cost_per_1k_output = PRICING[self.name]["output"] / 1000

    def screen(self, data_block: str) -> ScreenVerdict:
        # Skill content cache'lenir — sonraki tüm screen call'ları cache_read olur
        system = [
            {
                "type": "text",
                "text": self._system_skill,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        user_content = f"Ticker data block:\n\n{data_block}\n\nProvide your screen verdict via the tool."

        try:
            response = self._call(
                model=self.name,
                system=system,
                user_content=user_content,
                tools=[SCREEN_TOOL],
                tool_choice={"type": "tool", "name": "produce_screen"},
                max_tokens=512,
            )
        except APIError as e:
            logger.error(f"[CLAUDE-SCREEN] API hatası: {e}")
            ticker = "UNKNOWN"
            return ScreenVerdict(
                ticker=ticker,
                verdict="skip",
                rationale=f"API error: {e}",
                cost_usd=0.0,
            )

        # Ticker'ı data block'tan çıkarmak yerine response'tan döndürmek istemiyoruz —
        # caller (Stage 2) Candidate.ticker'ı zaten biliyor; rationale ve verdict kullanır.
        parsed = _extract_tool_input(response, "produce_screen") or {}
        cost = _calculate_cost(self.name, response.usage)
        logger.debug(
            f"[CLAUDE-SCREEN] tokens: in={response.usage.input_tokens} "
            f"out={response.usage.output_tokens} "
            f"cache_r={getattr(response.usage, 'cache_read_input_tokens', 0)} "
            f"cost=${cost:.5f}"
        )

        # Data block'tan ticker — robust regex
        import re

        m = re.search(r"\[(?:STOCK|COMMODITY):\s*(\S+)\s*\|", data_block)
        ticker = m.group(1) if m else "UNKNOWN"

        return ScreenVerdict(
            ticker=ticker,
            verdict=parsed.get("verdict", "skip"),
            rationale=parsed.get("rationale", ""),
            cost_usd=cost,
        )

    def deep_analyze(self, data_block: str) -> DeepAnalysis:
        raise NotImplementedError("Screen client deep_analyze yapmaz, ClaudeDeepClient kullan")


class ClaudeDeepClient(_BaseClaudeClient, LLMClient):
    """Stage 3 — Opus 4.7 ile deep analysis.

    Maliyet: ~$0.15-0.30 per ticker (cache hit ile $0.05).
    Bir run'da ~15 ticker → ~$3-5.
    """

    name = "claude-opus-4-7"

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key=api_key)
        self._system_skill = load_skill("deep-analyst")
        self.cost_per_1k_input = PRICING[self.name]["input"] / 1000
        self.cost_per_1k_output = PRICING[self.name]["output"] / 1000

    def screen(self, data_block: str) -> ScreenVerdict:
        raise NotImplementedError("Deep client screen yapmaz, ClaudeScreenClient kullan")

    def deep_analyze(self, data_block: str) -> DeepAnalysis:
        system = [
            {
                "type": "text",
                "text": self._system_skill,
                "cache_control": {"type": "ephemeral"},  # ~3500 token skill, cache'le
            }
        ]
        user_content = (
            f"Analyze the following ticker. Read Layer 0 first if MARKET AGENDA exists, "
            f"then proceed through Layers 1-6. Output via the produce_analysis tool.\n\n"
            f"```\n{data_block}\n```"
        )

        # Ticker'ı önceden çıkar (response'a koymak için)
        import re

        m = re.search(r"\[(?:STOCK|COMMODITY):\s*(\S+)\s*\|", data_block)
        ticker = m.group(1) if m else "UNKNOWN"

        try:
            response = self._call(
                model=self.name,
                system=system,
                user_content=user_content,
                tools=[DEEP_TOOL],
                tool_choice={"type": "tool", "name": "produce_analysis"},
                max_tokens=4096,
            )
        except APIError as e:
            logger.error(f"[CLAUDE-DEEP] {ticker} API hatası: {e}")
            return DeepAnalysis(
                ticker=ticker,
                signal="TUT",
                confidence=0.0,
                rationale_full=f"API error: {e}",
                warning_flags=["LLM_API_ERROR"],
                model=self.name,
                cost_usd=0.0,
            )

        parsed = _extract_tool_input(response, "produce_analysis")
        if not parsed:
            logger.error(f"[CLAUDE-DEEP] {ticker} tool_use bulunamadı")
            return DeepAnalysis(
                ticker=ticker,
                signal="TUT",
                confidence=0.0,
                rationale_full="No tool output from model",
                warning_flags=["LLM_NO_TOOL_OUTPUT"],
                model=self.name,
                cost_usd=_calculate_cost(self.name, response.usage),
            )

        cost = _calculate_cost(self.name, response.usage)
        logger.info(
            f"[CLAUDE-DEEP] {ticker}: signal={parsed.get('signal')} "
            f"conf={parsed.get('confidence', 0):.2f} "
            f"tokens(in/out/cache_r)={response.usage.input_tokens}/"
            f"{response.usage.output_tokens}/"
            f"{getattr(response.usage, 'cache_read_input_tokens', 0)} "
            f"cost=${cost:.4f}"
        )

        # Scenarios parse
        raw_scenarios = parsed.get("scenarios") or []
        scenarios = [
            PriceScenarioOutput(
                label=s["label"],
                target_price=float(s["target_price"]),
                probability=float(s["probability"]),
                expected_return_pct=float(s["expected_return_pct"]),
            )
            for s in raw_scenarios
            if "label" in s and "target_price" in s
        ]

        return DeepAnalysis(
            ticker=ticker,
            signal=parsed["signal"],
            confidence=float(parsed["confidence"]),
            entry_zone_low=parsed.get("entry_zone_low"),
            entry_zone_high=parsed.get("entry_zone_high"),
            stop_loss=parsed.get("stop_loss"),
            scenarios=scenarios,
            expected_return_pct=parsed.get("expected_return_pct"),
            time_horizon_days=parsed.get("time_horizon_days"),
            rationale_trend=parsed.get("rationale_trend", ""),
            rationale_formation=parsed.get("rationale_formation", ""),
            rationale_volume=parsed.get("rationale_volume", ""),
            rationale_news=parsed.get("rationale_news", ""),
            rationale_fibonacci=parsed.get("rationale_fibonacci", ""),
            rationale_risks=parsed.get("rationale_risks", []),
            rationale_full=parsed.get("rationale_full", ""),
            warning_flags=parsed.get("warning_flags", []),
            unsourced_flag=bool(parsed.get("unsourced_flag", False)),
            model=self.name,
            cost_usd=cost,
        )


__all__ = ["ClaudeDeepClient", "ClaudeScreenClient", "PRICING"]
