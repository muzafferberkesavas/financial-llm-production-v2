"""Multi-LLM voting ensemble — Vercel AI Gateway üzerinden Claude + GPT + Gemini paralel.

Akış:
    1. Aynı prompt 3 modele paralel gönderilir
    2. Her model structured JSON döner
    3. Voting: çoğunluk yönü, ortalama confidence
    4. Agreement skoru: 3/3 = 1.0, 2/3 = 0.66, 1/3 = 0.33 (anlaşmazlık)
    5. Disagreement varsa confidence düşürülür → daha güvenli kararlar
"""
from __future__ import annotations

import asyncio
import json
from collections import Counter
from dataclasses import dataclass

import httpx

from finllm.config.settings import settings
from finllm.signals.schema import ReasoningInput, ReasoningOutput
from finllm.utils.logging import logger

AI_GATEWAY_URL = "https://ai-gateway.vercel.sh/v1/chat/completions"

# Bu listeyi .env'den de yönetebilirsin (sonra eklenebilir).
# AI Gateway "provider/model" formatını bekler.
ENSEMBLE_MODELS = [
    "anthropic/claude-sonnet-4-6",
    "openai/gpt-5",
    "google/gemini-2.5-pro",
]

SYSTEM_PROMPT = """Sen kıdemli bir swing-trading analistisin (5-15 gün vade). \
Sana bir hisse için 50+ teknik gösterge, FinBERT sentiment skorları ve son haberler veriliyor.

Görev: AL/SAT/BEKLE (BUY/SELL/HOLD) kararı, güven skoru ve detaylı gerekçe üret.

Kurallar:
1. Bilmediğin şeyi uydurma — veriye dayan, gösterge isimlerini kullan
2. Karışık sinyaller varsa HOLD — gereksiz risk alma
3. Aşırı alım (RSI>70, Stoch>80) bölgesinde BUY önerirken çok dikkatli ol
4. Sentiment tek başına yetmez — teknikle uyumlu olmalı
5. Confidence 0.6 altındaysa HOLD tercih et
6. Risk faktörlerini açıkça yaz
7. Türkçe yanıt ver, gerekçen 4-6 cümle olsun ve hangi göstergelere baktığını belirt
8. Ichimoku, SuperTrend, MFI, CCI, Aroon, candle pattern, sentiment skoru gibi göstergeleri özellikle kullan

ÇIKTI FORMATI — SADECE geçerli JSON, başka metin yok, ```json fence yok:
{
  "direction": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0-1.0,
  "holdingDaysMin": int,
  "holdingDaysMax": int,
  "targetPrice": float | null,
  "stopLoss": float | null,
  "expectedReturn": float | null,
  "rationale": "4-6 cümle, hangi göstergelere baktığını belirt",
  "riskFactors": ["risk 1", "risk 2", "risk 3"],
  "technicalNote": "1-2 cümle teknik özet",
  "sentimentNote": "1-2 cümle sentiment özet"
}"""


@dataclass
class ModelVote:
    model: str
    output: ReasoningOutput | None
    error: str | None = None
    latency_ms: int = 0


@dataclass
class EnsembleResult:
    final_output: ReasoningOutput
    votes: list[ModelVote]
    agreement_score: float          # 1.0 = tam mutabakat
    direction_counts: dict[str, int]


def _build_user_msg(inp: ReasoningInput) -> str:
    return f"""Sembol: {inp.symbol}
Mevcut fiyat: ${inp.currentPrice:.2f}

TEKNİK GÖSTERGELER (50+):
{json.dumps(inp.technical, indent=2)}

SENTIMENT:
{json.dumps(inp.sentiment, indent=2)}

SON HABERLER:
{json.dumps(inp.recentNews[:10], indent=2, default=str) if inp.recentNews else "(haber yok)"}

Yukarıdaki tüm verileri analiz et ve JSON kararını ver."""


def _extract_json(text: str) -> str:
    """Modellerin bazen eklediği fence/açıklamayı temizle."""
    t = text.strip()
    if "```json" in t:
        t = t.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in t:
        t = t.split("```", 1)[1].split("```", 1)[0]
    # İlk { ve son } arasını al
    first = t.find("{")
    last = t.rfind("}")
    if first >= 0 and last > first:
        t = t[first : last + 1]
    return t.strip()


async def _call_one(
    client: httpx.AsyncClient,
    model: str,
    system: str,
    user: str,
) -> ModelVote:
    import time
    t0 = time.time()
    try:
        resp = await client.post(
            AI_GATEWAY_URL,
            headers={
                "Authorization": f"Bearer {settings.ai_gateway_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": 1500,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(_extract_json(content))
        output = ReasoningOutput(**parsed)
        return ModelVote(model=model, output=output, latency_ms=int((time.time() - t0) * 1000))
    except Exception as e:
        logger.warning(f"{model}: {type(e).__name__}: {e}")
        return ModelVote(model=model, output=None, error=str(e), latency_ms=int((time.time() - t0) * 1000))


async def _vote_async(inp: ReasoningInput, models: list[str]) -> EnsembleResult:
    if not settings.ai_gateway_api_key:
        raise RuntimeError("AI_GATEWAY_API_KEY .env'de tanımlı değil")
    user = _build_user_msg(inp)
    async with httpx.AsyncClient() as client:
        votes = await asyncio.gather(*[_call_one(client, m, SYSTEM_PROMPT, user) for m in models])
    return aggregate(votes)


def aggregate(votes: list[ModelVote]) -> EnsembleResult:
    successful = [v for v in votes if v.output is not None]
    if not successful:
        raise RuntimeError(f"Tüm modeller başarısız: {[(v.model, v.error) for v in votes]}")

    directions = [v.output.direction for v in successful]
    counts = Counter(directions)
    majority_dir = counts.most_common(1)[0][0]
    n = len(successful)
    agreement = counts[majority_dir] / n     # 1.0 = tam, 0.66 = 2/3, 0.5 = 2/4

    majority_votes = [v for v in successful if v.output.direction == majority_dir]
    avg_conf = sum(v.output.confidence for v in majority_votes) / len(majority_votes)
    final_conf = avg_conf * agreement        # anlaşmazlık varsa düşür

    # Saysal alanları çoğunluk oylarından ortalama
    def _avg(field: str) -> float | None:
        vals = [getattr(v.output, field) for v in majority_votes if getattr(v.output, field) is not None]
        return sum(vals) / len(vals) if vals else None

    avg_target = _avg("targetPrice")
    avg_stop = _avg("stopLoss")
    avg_ret = _avg("expectedReturn")
    hold_min = round(_avg("holdingDaysMin") or 5)
    hold_max = round(_avg("holdingDaysMax") or 15)

    # Rasyonelleri birleştir
    rationale_parts = []
    risks: list[str] = []
    tech_notes = []
    sent_notes = []
    for v in successful:
        provider = v.model.split("/", 1)[0]
        rationale_parts.append(f"[{provider}] {v.output.rationale}")
        risks.extend(v.output.riskFactors)
        tech_notes.append(v.output.technicalNote)
        sent_notes.append(v.output.sentimentNote)

    disagreement_note = ""
    if agreement < 1.0:
        disagree = [v for v in successful if v.output.direction != majority_dir]
        notes = "; ".join(f"{v.model.split('/',1)[0]} → {v.output.direction}" for v in disagree)
        disagreement_note = f" Anlaşmazlık: {notes}."

    final = ReasoningOutput(
        direction=majority_dir,
        confidence=round(final_conf, 3),
        holdingDaysMin=hold_min,
        holdingDaysMax=hold_max,
        targetPrice=avg_target,
        stopLoss=avg_stop,
        expectedReturn=avg_ret,
        rationale=(
            f"Ensemble kararı: {counts[majority_dir]}/{n} model {majority_dir} dedi"
            f" (agreement {agreement:.0%}).{disagreement_note}\n\n"
            + "\n\n".join(rationale_parts)
        ),
        riskFactors=list(dict.fromkeys(risks))[:6],   # dedupe + cap
        technicalNote=" | ".join(tech_notes),
        sentimentNote=" | ".join(sent_notes),
    )
    return EnsembleResult(
        final_output=final,
        votes=votes,
        agreement_score=agreement,
        direction_counts=dict(counts),
    )


def vote(inp: ReasoningInput, models: list[str] | None = None) -> EnsembleResult:
    """Senkron sarmalayıcı. Default: ENSEMBLE_MODELS."""
    models = models or ENSEMBLE_MODELS
    return asyncio.run(_vote_async(inp, models))


def reason_ensemble(inp: ReasoningInput) -> ReasoningOutput:
    """claude_reasoner.reason ile aynı imza — drop-in replacement.

    AI Gateway başarısız olursa (yetki/CC/quota), single Claude'a düşer.
    """
    from finllm.ensemble.claude_reasoner import reason as reason_single

    try:
        result = vote(inp)
        logger.info(
            f"{inp.symbol}: {result.final_output.direction} "
            f"(agreement {result.agreement_score:.0%}, {result.direction_counts})"
        )
        return result.final_output
    except RuntimeError as e:
        logger.warning(
            f"⚠️  Ensemble başarısız ({e}). Single Claude moduna düşülüyor. "
            f"AI Gateway için Vercel'e kredi kartı eklemen gerekebilir."
        )
        return reason_single(inp)
