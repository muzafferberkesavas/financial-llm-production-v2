"""FinBERT sentiment scorer — ProsusAI/finbert (üç sınıflı: positive/neutral/negative)."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

# NOT: torch/transformers ağır ve opsiyonel ("nlp" extra). Bu modülü import etmek
# torch kurulu olmadan da çökmemeli — gerçek importlar fonksiyon içinde (lazy) yapılır.
from finllm.utils.logging import logger

MODEL_ID = "ProsusAI/finbert"
LABELS = ["positive", "negative", "neutral"]


@dataclass
class SentimentResult:
    text: str
    label: str
    score: float  # confidence of chosen label
    polarity: float  # positive - negative ∈ [-1, 1]


@lru_cache(maxsize=1)
def _load():
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "FinBERT için torch/transformers gerekli ama kurulu değil. "
            "Kur: `pip install -e '.[nlp]'` — veya SENTIMENT_PROVIDER=disabled kullan."
        ) from e
    device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"FinBERT yükleniyor (device={device})")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID).to(device)
    model.eval()
    return tokenizer, model, device


def score_batch(texts: list[str], batch_size: int = 16) -> list[SentimentResult]:
    if not texts:
        return []
    import torch  # lazy — _load() zaten torch yoksa anlamlı hata verir

    tokenizer, model, device = _load()
    results: list[SentimentResult] = []

    with torch.inference_mode():
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            enc = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt",
            ).to(device)
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
            for text, p in zip(batch, probs):
                idx = int(p.argmax())
                results.append(
                    SentimentResult(
                        text=text,
                        label=LABELS[idx],
                        score=float(p[idx]),
                        polarity=float(p[0] - p[1]),  # pos - neg
                    )
                )
    return results


def score_one(text: str) -> SentimentResult:
    return score_batch([text])[0]


def aggregate_polarity(results: list[SentimentResult]) -> float:
    """Confidence-weighted mean polarity. Çıktı ∈ [-1, 1]."""
    if not results:
        return 0.0
    weights = [r.score for r in results]
    weighted = sum(r.polarity * w for r, w in zip(results, weights))
    return weighted / sum(weights)
