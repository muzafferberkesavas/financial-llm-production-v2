"""FinGPT-Forecaster — geçmiş fiyatlar + haber özetleri verilince gelecek hafta yön + gerekçe.

Model FinGPT/fingpt-forecaster_dow30_llama2-7b_lora özel bir prompt formatı bekler;
ana ekibin notebook'undan adapte edilmiştir (https://github.com/AI4Finance-Foundation/FinGPT).
"""
from __future__ import annotations

import re

import torch
from loguru import logger

from app.models_loader import load_forecaster

PROMPT = """[INST]<<SYS>>
You are a seasoned stock market analyst. Your task is to list the positive developments and potential concerns for companies based on relevant news and basic financials from the past weeks, then provide an analysis and prediction for the companies' stock price movement for the upcoming week. Your answer format should be as follows:

[Positive Developments]:
1. ...

[Potential Concerns]:
1. ...

[Prediction & Analysis]:
Prediction: ...
Analysis: ...
<</SYS>>

[Company Introduction]:
{company}

[Recent Stock Price Movements]:
{price_recap}

[News from the past 4 weeks]:
{news_block}

[Basic Financials]:
{financials}

Based on all the information before, let's first analyze the positive developments and potential concerns for {symbol}. Come up with 2-4 most important factors respectively and keep them concise. Most factors should be inferred from company related news. Then make your prediction of the {symbol} stock price movement for next week. Provide a summary analysis to support your prediction.[/INST]"""


def _parse_prediction(text: str) -> dict:
    # Beklenen: "Prediction: up by X%" / "down by Y%" / "flat"
    direction = "FLAT"
    pct = 0.0
    m = re.search(r"prediction[:\s]+(up|down|flat)(?:\s+by\s+([\d.]+)\s*%?)?", text, re.IGNORECASE)
    if m:
        direction = m.group(1).upper()
        if m.group(2):
            pct = float(m.group(2))
    # Sections
    def _sec(name: str) -> list[str]:
        pat = rf"\[{name}\][:\s]*(.+?)(?=\[|$)"
        mm = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if not mm:
            return []
        body = mm.group(1).strip()
        items = re.findall(r"\d+\.\s+(.+?)(?=\n\d+\.|\n\n|$)", body, re.DOTALL)
        return [i.strip() for i in items if i.strip()]
    return {
        "direction": direction,           # UP / DOWN / FLAT
        "expectedChangePct": pct,
        "positives": _sec("Positive Developments"),
        "concerns": _sec("Potential Concerns"),
        "analysis": text,
    }


def forecast(
    symbol: str,
    company: str,
    price_recap: str,
    news_block: str,
    financials: str = "",
    max_new_tokens: int = 600,
) -> dict:
    tokenizer, model, device = load_forecaster()
    prompt = PROMPT.format(
        symbol=symbol,
        company=company,
        price_recap=price_recap,
        news_block=news_block,
        financials=financials or "N/A",
    )
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096)
    if device != "cpu":
        inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.inference_mode():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=0.0,
            pad_token_id=tokenizer.eos_token_id,
        )
    decoded = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    parsed = _parse_prediction(decoded)
    parsed["symbol"] = symbol
    return parsed
