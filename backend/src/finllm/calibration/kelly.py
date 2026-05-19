"""Kelly criterion — position sizing using calibrated probability.

f* = (p × b − q) / b
where:
  p = calibrated probability of win
  q = 1 − p
  b = win/loss ratio (avg_win / abs(avg_loss))

Fractional Kelly: f_pos = min(f*, max_position_pct) × kelly_fraction (genelde 0.5)
Why fractional: full Kelly variansı çok yüksek; pratik trader'lar 0.25-0.5 Kelly.

Phase 2.4'te basit per-signal Kelly, Phase 3'te per-strategy ensemble Kelly.
"""
from __future__ import annotations


def kelly_fraction(
    win_probability: float,
    win_loss_ratio: float,
    kelly_multiplier: float = 0.5,
    max_fraction: float = 0.25,
) -> float:
    """Kelly fraction: paranın ne kadarı tek pozisyona girer (0-max_fraction).

    Args:
        win_probability: calibrated_probability (0-1)
        win_loss_ratio: avg_win / abs(avg_loss) — örn 2.0 means winners are 2x losers
        kelly_multiplier: 0.25=quarter, 0.5=half, 1.0=full Kelly (riskli)
        max_fraction: tek pozisyonda ne kadar — default 0.25

    Returns:
        f_pos in [0, max_fraction]
    """
    p = max(0.0, min(1.0, win_probability))
    q = 1.0 - p
    b = max(0.01, win_loss_ratio)

    f_star = (p * b - q) / b
    if f_star <= 0:
        return 0.0  # Edge yok, pozisyon alma

    fractional = f_star * kelly_multiplier
    return min(fractional, max_fraction)


def recommend_kelly_size(
    calibrated_probability: float,
    target_return_pct: float,
    stop_loss_pct: float,
    total_capital: float,
    kelly_multiplier: float = 0.5,
    max_position_pct: float = 0.25,
) -> dict:
    """Bir sinyal için Kelly tabanlı önerilen position size.

    Args:
        calibrated_probability: PlattCalibrator çıktısı (raw confidence değil)
        target_return_pct: base scenario expected return %
        stop_loss_pct: stop_loss'a düşüş % (negatif değer)

    Returns:
        {
            "kelly_fraction": float,         # of capital
            "position_size_cash": float,
            "win_loss_ratio": float,
            "expected_value": float,         # EV per dollar
            "recommendation": "FULL" | "NORMAL" | "SMALL" | "MINIMAL" | "SKIP",
        }
    """
    # Win/loss ratio
    if stop_loss_pct >= 0:
        # Stop yoksa veya pozitif (mantıksız) — Kelly hesaplanamaz
        return {
            "kelly_fraction": 0.0,
            "position_size_cash": 0.0,
            "win_loss_ratio": 0.0,
            "expected_value": 0.0,
            "recommendation": "SKIP",
        }

    win_loss_ratio = abs(target_return_pct / stop_loss_pct)
    f = kelly_fraction(
        calibrated_probability,
        win_loss_ratio,
        kelly_multiplier=kelly_multiplier,
        max_fraction=max_position_pct,
    )

    # Expected value per dollar invested
    p = calibrated_probability
    ev_per_dollar = p * (target_return_pct / 100) + (1 - p) * (stop_loss_pct / 100)

    if f >= 0.20:
        rec = "FULL"
    elif f >= 0.12:
        rec = "NORMAL"
    elif f >= 0.06:
        rec = "SMALL"
    elif f > 0:
        rec = "MINIMAL"
    else:
        rec = "SKIP"

    return {
        "kelly_fraction": round(f, 4),
        "position_size_cash": round(total_capital * f, 2),
        "win_loss_ratio": round(win_loss_ratio, 2),
        "expected_value": round(ev_per_dollar, 4),
        "recommendation": rec,
    }


__all__ = ["kelly_fraction", "recommend_kelly_size"]
