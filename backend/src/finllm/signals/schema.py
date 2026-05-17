"""Sinyal şemaları — backend ↔ dashboard arasında ortak kontrat."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Direction = Literal["BUY", "SELL", "HOLD"]


class HoldingDays(BaseModel):
    min: int
    max: int


class FactorScore(BaseModel):
    score: float = Field(..., ge=-1.0, le=1.0)
    notes: str


class SignalFactors(BaseModel):
    technical: FactorScore
    sentiment: FactorScore
    fundamental: FactorScore | None = None


class Signal(BaseModel):
    symbol: str
    direction: Direction
    confidence: float = Field(..., ge=0.0, le=1.0)
    holdingDays: HoldingDays
    entryPrice: float
    targetPrice: float | None = None
    stopLoss: float | None = None
    expectedReturn: float | None = None
    rationale: str
    riskFactors: list[str] = Field(default_factory=list)
    signals: SignalFactors
    generatedAt: datetime = Field(default_factory=datetime.utcnow)


class ReasoningInput(BaseModel):
    """Claude'a beslenecek özetlenmiş girdi."""
    symbol: str
    currentPrice: float
    technical: dict
    sentiment: dict
    recentNews: list[dict] = Field(default_factory=list)


class ReasoningOutput(BaseModel):
    """Claude'dan beklenen structured cevap."""
    direction: Direction
    confidence: float = Field(..., ge=0.0, le=1.0)
    holdingDaysMin: int = Field(..., ge=0)
    holdingDaysMax: int = Field(..., ge=0)
    targetPrice: float | None = None
    stopLoss: float | None = None
    expectedReturn: float | None = None
    rationale: str
    riskFactors: list[str] = Field(default_factory=list)
    technicalNote: str
    sentimentNote: str
