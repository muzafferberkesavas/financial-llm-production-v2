"""Analiz sonuclarini guzel yazdir."""
import json, sys

d = json.load(sys.stdin)
print(f"Status: {d['status']}")
print(f"Duration: {d.get('duration_sec',0)}s | Cost: ${d.get('total_cost_usd',0)}")
print(f"Universe: {d.get('universe_size',0)} | Filter: {d.get('passed_filter',0)} | Analyzed: {d.get('analyzed_count',0)}")
print(f"Signals: {len(d['signals'])} | BUY: {len(d['buy_signals'])}")
print()

for s in d["signals"]:
    print("=" * 80)
    print(f"{s['ticker']} ({s['name']}) - {s['sector']}")
    msp = s.get("master_score_pct") or 0
    print(f"  Sinyal: {s['signal']} | Guven: {s['confidence']:.0%} | Master Score: {msp:.0f}%")
    print(f"  Giris: {s.get('entry_zone_low','-')} - {s.get('entry_zone_high','-')} | Stop: {s.get('stop_loss','-')}")
    print(f"  Beklenen Getiri: {s.get('expected_return_pct','-')}% | Vade: {s.get('time_horizon_days','-')} gun")
    print()

    for sc in s.get("scenarios", []):
        print(f"  [{sc['label'].upper():5s}] Hedef: {sc['target_price']:.2f} | Olasilik: {sc['probability']:.0%} | Getiri: {sc['expected_return_pct']:+.1f}%")
    print()

    r = s.get("rationale", {})
    if r.get("trend"):     print(f"  TREND: {r['trend']}")
    if r.get("formation"): print(f"  FORMASYON: {r['formation']}")
    if r.get("volume"):    print(f"  HACIM: {r['volume']}")
    if r.get("fibonacci"): print(f"  FIBONACCI: {r['fibonacci']}")
    if r.get("news"):      print(f"  HABERLER: {r['news']}")
    if r.get("full"):      print(f"\n  DEGERLENDIRME: {r['full']}")
    if r.get("risks"):
        print("  RISKLER:")
        for risk in r["risks"]:
            print(f"    - {risk}")
    if s.get("warning_flags"):
        print(f"  UYARILAR: {', '.join(s['warning_flags'])}")
    print(f"  LLM: {s['llm_model']} | Maliyet: ${s['llm_cost_usd']:.4f}")
    print()
