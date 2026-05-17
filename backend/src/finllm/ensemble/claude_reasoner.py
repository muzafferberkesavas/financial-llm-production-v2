"""Claude meta-karar katmanı. Tüm alt-sinyalleri okur, structured BUY/SELL/HOLD üretir."""
from __future__ import annotations

import json

from anthropic import Anthropic

from finllm.config.settings import settings
from finllm.signals.schema import ReasoningInput, ReasoningOutput
from finllm.utils.logging import logger

CLAUDE_MODEL = "claude-sonnet-4-6"  # hızlı + ucuz; Opus üretim için sonra denenebilir

SYSTEM_PROMPT = """Sen kıdemli bir swing-trading analistisin (5-15 gün vade). \
Sana bir hisse için teknik göstergeler, FinBERT sentiment skorları ve son haberler veriliyor.

Görev: AL/SAT/BEKLE (BUY/SELL/HOLD) kararı, güven skoru ve gerekçe üret.

Önemli kurallar:
1. Bilmediğin şeyi uydurma — veriye dayan
2. Karışık sinyaller varsa HOLD ver, gereksiz risk alma
3. Aşırı alım (RSI>70) bölgesinde BUY önerirken çok dikkatli ol
4. Sentiment tek başına yetmez — teknikle uyumlu olmalı
5. Confidence 0.6 altındaysa HOLD tercih et
6. Risk faktörlerini açıkça yaz
7. Türkçe yanıt ver

ÇIKTI FORMATI — sadece geçerli JSON, başka metin yok:
{
  "direction": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0-1.0,
  "holdingDaysMin": int,
  "holdingDaysMax": int,
  "targetPrice": float | null,
  "stopLoss": float | null,
  "expectedReturn": float | null,
  "rationale": "3-5 cümle gerekçe",
  "riskFactors": ["risk 1", "risk 2"],
  "technicalNote": "1 cümle",
  "sentimentNote": "1 cümle"
}
"""


def reason(input_data: ReasoningInput) -> ReasoningOutput:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY .env'de tanımlı değil")

    client = Anthropic(api_key=settings.anthropic_api_key)

    user_msg = f"""Sembol: {input_data.symbol}
Mevcut fiyat: ${input_data.currentPrice:.2f}

TEKNİK GÖSTERGELER:
{json.dumps(input_data.technical, indent=2)}

SENTIMENT (FinBERT):
{json.dumps(input_data.sentiment, indent=2)}

SON HABERLER:
{json.dumps(input_data.recentNews[:10], indent=2, default=str) if input_data.recentNews else "(haber yok)"}

Şimdi yukarıdaki kurallara göre kararını JSON formatında ver."""

    logger.info(f"Claude'a istek gönderiliyor: {input_data.symbol}")
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        temperature=0.2,
    )

    text = "".join(block.text for block in resp.content if hasattr(block, "text"))
    # JSON parse — Claude bazen ```json fence ekler, temizleyelim
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Claude JSON parse failed: {e}\nRaw:\n{text}")
        raise

    return ReasoningOutput(**data)
