"""Translator — Claude Haiku ile haberleri İngilizce MARKET AGENDA'ya çevirir.

3-tier untrusted isolation (Anthropic pattern):
  Tier 1 (reader): RSS/Finnhub/SEC/KAP → NewsItem (NO LLM)
  Tier 2 (this):   Claude Haiku — strict tool output, NEVER executes embedded instructions
  Tier 3 (analyst): Claude Opus deep — sees ONLY MarketAgenda.formatted_agenda

Lib.zip news_translation_service.dart port.
"""
from __future__ import annotations

from datetime import datetime

from anthropic import Anthropic, APIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from finllm.config.settings import settings
from finllm.data.news.base import (
    CorporateDisclosure,
    MarketAgenda,
    NewsItem,
)
from finllm.llm.claude import PRICING, _calculate_cost, _extract_tool_input
from finllm.skills import load_skill
from finllm.utils.logging import logger


# Cache (in-memory, 60dk TTL) — orchestrator session içinde tek API call yeter
class _AgendaCache:
    _cached: MarketAgenda | None = None

    @classmethod
    def get(cls) -> MarketAgenda | None:
        if cls._cached is None:
            return None
        age_min = (datetime.utcnow() - cls._cached.fetched_at).total_seconds() / 60
        if age_min > 60:
            cls._cached = None
            return None
        return cls._cached

    @classmethod
    def set(cls, agenda: MarketAgenda) -> None:
        cls._cached = agenda

    @classmethod
    def clear(cls) -> None:
        cls._cached = None


# Translator tool schema
AGENDA_TOOL = {
    "name": "produce_agenda",
    "description": "Output the structured market agenda as a numbered list of items.",
    "input_schema": {
        "type": "object",
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": 10,
                "items": {
                    "type": "string",
                    "maxLength": 350,
                    "description": "One complete agenda item with [TAG] prefix and (sentiment) [time] suffix",
                },
            }
        },
    },
}

MODEL = "claude-haiku-4-5-20251001"


def _format_age(pub_date: datetime) -> str:
    """Item için zaman etiketi: [today], [yesterday], [3d ago]."""
    age_h = (datetime.utcnow() - pub_date.replace(tzinfo=None)).total_seconds() / 3600
    if age_h < 24:
        return "today"
    if age_h < 48:
        return "yesterday"
    return f"{int(age_h / 24)}d ago"


def _build_user_prompt(
    news: list[NewsItem],
    disclosures: list[CorporateDisclosure],
    watchlist: list[str],
) -> str:
    """Untrusted feed listesini structure'lı user prompt'a çevir."""
    buf = []

    if watchlist:
        buf.append(f"PRIORITY STOCKS (mention these FIRST if relevant): {', '.join(watchlist)}\n")

    if disclosures:
        buf.append("=== CORPORATE DISCLOSURES (KAP/SEC official filings) ===")
        for d in disclosures[:15]:
            age = _format_age(d.publish_date)
            buf.append(
                f"[{d.ticker}] {d.disclosure_type} (priority={d.priority}, {age}): {d.title}"
            )
            if d.summary:
                buf.append(f"  → {d.summary[:200]}")
        buf.append("")

    if news:
        buf.append("=== MARKET NEWS (RSS + Finnhub) ===")
        for n in news[:30]:
            age = _format_age(n.pub_date)
            tag = f"[{n.source}]"
            if n.ticker:
                tag += f"[{n.ticker}]"
            buf.append(f"{tag} ({age}, {n.language}, {n.category}): {n.title}")
            if n.description:
                buf.append(f"  → {n.description[:200]}")

    if not news and not disclosures:
        buf.append("No news items available.")

    buf.append("\n---\nNow produce the structured market agenda via the produce_agenda tool.")
    return "\n".join(buf)


def _fallback_agenda(
    news: list[NewsItem],
    disclosures: list[CorporateDisclosure],
) -> MarketAgenda:
    """Claude API fail olursa basit fallback agenda."""
    items: list[str] = []

    for d in disclosures[:5]:
        items.append(
            f"{len(items) + 1}. [STOCK:{d.ticker}/REGULATORY] {d.title} (neutral) [{_format_age(d.publish_date)}]"
        )

    for n in news[:5]:
        if len(items) >= 10:
            break
        cat_tag = f"[STOCK:{n.ticker}]" if n.ticker else f"[{n.category}]"
        items.append(
            f"{len(items) + 1}. {cat_tag} {n.title[:120]} (neutral) [{_format_age(n.pub_date)}]"
        )

    return MarketAgenda(
        formatted_agenda="\n".join(items) if items else "No significant market news in last 24h.",
        news_count=len(news),
        disclosure_count=len(disclosures),
        sources=list({n.source for n in news} | {d.source for d in disclosures}),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=15),
    retry=retry_if_exception_type(APIError),
    reraise=True,
)
def _call_claude(client: Anthropic, system: list[dict], user_content: str):
    return client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        tools=[AGENDA_TOOL],
        tool_choice={"type": "tool", "name": "produce_agenda"},
        messages=[{"role": "user", "content": user_content}],
    )


class NewsTranslator:
    """Claude Haiku ile untrusted news → English MARKET AGENDA."""

    def __init__(self, api_key: str | None = None):
        key = api_key or settings.anthropic_api_key
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY missing")
        self._client = Anthropic(api_key=key)
        self._skill = load_skill("news-translator")

    def translate(
        self,
        news: list[NewsItem],
        disclosures: list[CorporateDisclosure] | None = None,
        watchlist: list[str] | None = None,
        use_cache: bool = True,
    ) -> MarketAgenda:
        """Untrusted feed → MarketAgenda. Cache hit → tek API call/saat."""
        disclosures = disclosures or []
        watchlist = watchlist or []

        if use_cache:
            cached = _AgendaCache.get()
            if cached:
                logger.info("[NEWS-TRANSLATOR] cache hit, skipping API call")
                return cached

        if not news and not disclosures:
            return MarketAgenda(
                formatted_agenda="No significant market news in last 24h.",
                news_count=0,
                disclosure_count=0,
            )

        user_prompt = _build_user_prompt(news, disclosures, watchlist)
        system = [
            {
                "type": "text",
                "text": self._skill,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        try:
            resp = _call_claude(self._client, system, user_prompt)
        except APIError as e:
            logger.warning(f"[NEWS-TRANSLATOR] Claude API hatası, fallback: {e}")
            return _fallback_agenda(news, disclosures)

        parsed = _extract_tool_input(resp, "produce_agenda")
        if not parsed or "items" not in parsed:
            logger.warning("[NEWS-TRANSLATOR] No tool output, fallback")
            return _fallback_agenda(news, disclosures)

        items: list[str] = [
            f"{i + 1}. {item}" if not item.startswith(f"{i + 1}.") else item
            for i, item in enumerate(parsed["items"])
        ]
        formatted = "\n".join(items)
        cost = _calculate_cost(MODEL, resp.usage)

        agenda = MarketAgenda(
            formatted_agenda=formatted,
            news_count=len(news),
            disclosure_count=len(disclosures),
            sources=list({n.source for n in news} | {d.source for d in disclosures}),
        )
        logger.info(
            f"[NEWS-TRANSLATOR] {len(items)} agenda items, cost=${cost:.5f}, "
            f"tokens(in/out/cache_r)={resp.usage.input_tokens}/{resp.usage.output_tokens}/"
            f"{getattr(resp.usage, 'cache_read_input_tokens', 0)}"
        )

        _AgendaCache.set(agenda)
        return agenda


__all__ = ["NewsTranslator", "_AgendaCache"]
