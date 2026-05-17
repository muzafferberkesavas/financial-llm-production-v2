"""FinGPT-Sentiment — Llama-2 + LoRA, instruction-formatted prompt.

FinGPT'nin önerdiği prompt formatı:
    Instruction: What is the sentiment of this news? Please choose an answer from {strong negative/moderately negative/mildly negative/neutral/mildly positive/moderately positive/strong positive}.
    Input: <news text>
    Answer:
"""
from __future__ import annotations

import re

import torch
from loguru import logger

from app.models_loader import load_sentiment

# FinGPT'nin 7-sınıflı çıktısı → polarity ∈ [-1, 1] eşlemesi
LABEL_POLARITY = {
    "strong negative": -1.0,
    "moderately negative": -0.66,
    "mildly negative": -0.33,
    "neutral": 0.0,
    "mildly positive": 0.33,
    "moderately positive": 0.66,
    "strong positive": 1.0,
}

PROMPT_TEMPLATE = (
    "Instruction: What is the sentiment of this news? "
    "Please choose an answer from {{strong negative/moderately negative/mildly negative/"
    "neutral/mildly positive/moderately positive/strong positive}}.\n"
    "Input: {text}\n"
    "Answer:"
)


def _parse_label(generated: str) -> tuple[str, float]:
    """Üretilen cevaptan etiketi çıkar."""
    text = generated.lower().strip()
    # En uzun eşleşeni bul (örn. "moderately negative" "negative" üzerine)
    best = None
    for label in sorted(LABEL_POLARITY.keys(), key=len, reverse=True):
        if label in text:
            best = label
            break
    if best is None:
        # Fallback: positive/negative/neutral
        for short in ["positive", "negative", "neutral"]:
            if short in text:
                best = f"mildly {short}" if short != "neutral" else "neutral"
                break
    if best is None:
        return ("neutral", 0.0)
    return (best, LABEL_POLARITY[best])


def score_batch(texts: list[str], max_new_tokens: int = 12) -> list[dict]:
    if not texts:
        return []
    tokenizer, model, device = load_sentiment()
    results: list[dict] = []

    for text in texts:
        prompt = PROMPT_TEMPLATE.format(text=text[:1000])
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
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
        label, polarity = _parse_label(decoded)
        # Güven skoru: extreme etiketler daha güvenli kabul edilir
        score = min(1.0, 0.5 + abs(polarity) * 0.5)
        results.append({
            "label": label,
            "score": round(score, 3),
            "polarity": round(polarity, 3),
        })
    return results
