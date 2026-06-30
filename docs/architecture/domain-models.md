# Domain Modelleri

Tum veri kontratları Pydantic modelleri ile tanımlanır.

## Signal (`signals/schema.py`)

```python
class Signal(BaseModel):
    symbol: str
    direction: Literal["BUY", "SELL", "HOLD"]
    confidence: float              # 0-1
    holdingDays: HoldingDays       # min/max
    entryPrice: float
    targetPrice: float | None
    stopLoss: float | None
    expectedReturn: float | None
    rationale: str
    riskFactors: list[str]
    signals: SignalFactors         # technical, sentiment, fundamental skorları
    generatedAt: datetime
```

## Position (`portfolio/models.py`)

```python
class Position(BaseModel):
    id: int | None
    symbol: str
    entry_price: float
    entry_date: datetime
    target_price: float | None
    stop_loss: float | None
    max_holding_days: int
    weight_pct: float
    capital_usd: float
    exit_price: float | None
    exit_date: datetime | None
    exit_reason: ExitReason        # TARGET_HIT, STOP_HIT, MAX_HOLDING, SIGNAL_FLIP, NEGATIVE_NEWS
    pnl_pct: float | None
    pnl_usd: float | None
    status: Literal["open", "closed"]
```

## Order (`portfolio/models.py`)

```python
class Order(BaseModel):
    id: int | None
    symbol: str
    side: Literal["BUY", "SELL"]
    status: Literal["pending", "executed", "cancelled"]
    suggested_price: float
    target_price: float | None
    stop_loss: float | None
    weight_pct: float | None
    capital_usd: float | None
    related_position_id: int | None
```

## PortfolioSnapshot (`portfolio/models.py`)

```python
class PortfolioSnapshot(BaseModel):
    initial_capital_usd: float
    deployed_capital_usd: float
    open_positions: list[Position]
    pending_orders: list[Order]
    realized_pnl_usd: float
    open_pnl_usd: float
    total_value_usd: float
    n_open: int
    n_pending: int
```

## DeepAnalysis (`llm/base.py`)

```python
@dataclass
class DeepAnalysis:
    ticker: str
    signal: Literal[
        "GUCLU_AL", "AL", "IZLE", "TUT",
        "KISMI_SAT", "SAT", "ACIL_SAT"
    ]
    confidence: float              # 0-1
    entry_zone_low: float | None
    entry_zone_high: float | None
    stop_loss: float | None
    scenarios: list[PriceScenarioOutput]  # base/bull/bear
    rationale_trend: str
    rationale_formation: str
    rationale_volume: str
    rationale_news: str
    rationale_risks: list[str]
    rationale_full: str
    warning_flags: list[str]
    unsourced_flag: bool
    cost_usd: float
```

## ScreenVerdict (`llm/base.py`)

```python
@dataclass
class ScreenVerdict:
    ticker: str
    verdict: Literal["strong", "potential", "skip"]
    rationale: str
    cost_usd: float
```

## PriceScenarioOutput (`llm/base.py`)

```python
@dataclass
class PriceScenarioOutput:
    label: Literal["base", "bull", "bear"]
    target_price: float
    probability: float
    expected_return_pct: float
```
