# LLM Kullanimi

## Model Tiering

| Model | Kullanim Yeri | Yaklasik Maliyet |
|-------|---------------|------------------|
| **Haiku 4.5** | Stage 2 screening, debate adversary | ~$0.001-0.002/ticker |
| **Opus** | Stage 3 deep analysis | ~$0.15-0.30/ticker |
| **Sonnet 4.6** | Debate judge, macro-sector analyst | ~$0.01-0.02/ticker |
| **Mock** | Test, gelistirme | $0 |

## Client Dosyalari

| Dosya | Sinif | Amac |
|-------|-------|------|
| `llm/claude.py` | `ClaudeScreenClient` | Haiku ile ucuz tarama |
| `llm/claude.py` | `ClaudeDeepClient` | Opus ile derin analiz |
| `llm/mock.py` | `MockScreenClient` / `MockDeepClient` | Deterministik test |
| `llm/debate.py` | — | Bull/bear adversary + judge pattern |
| `llm/macro_sector.py` | — | Makro → sektor top-down tahsis |
| `llm/base.py` | `LLMClient` protocol | Arayüz tanimı |

## Skills (System Prompt'lar)

`backend/src/finllm/skills/` altinda markdown dosyalari olarak yasar. Prompt caching ile %90 maliyet azaltma saglanir.

| Dizin | Rol | Anthropic Pattern |
|-------|-----|-------------------|
| `cheap-screener/` | Haiku tarama — multi-lens screening (momentum, setup, volume, valuation, risk) | idea-generation screen framework |
| `deep-analyst/` | Opus derin analiz — 7 katman + senaryolar + catalyst awareness + peer valuation + thesis falsifiability | earnings-preview + comps-analysis + thesis-tracker |
| `debate-adversary/` | Haiku adversary — 4-boyutlu argument framework (teknik, temel, makro, catalyst) | market-researcher steelman pattern |
| `debate-judge/` | Sonnet judge — red flags checklist + thesis invalidation + anti-crowding | comps red flags + thesis falsifiability |
| `macro-sector-analyst/` | Sektor istahi (0-1, 12 sektor) | sector-overview market dynamics |
| `news-translator/` | Claude haber ceviri (TR → EN) + untrusted input security | — (zaten Anthropic seviyesinde) |

## Maliyet Takibi

Her LLM cagrisi `cost_usd` döndürür (input/output/cache token sayisindan hesaplanir). `PipelineContext.total_cost_usd` toplam calistirma maliyetini tutar.

## Ensemble

`ensemble/multi_llm_voter.py` — Claude + OpenAI + Google oylama destegi. Fallback: yalnizca Claude.

## Sentiment

`sentiment/provider.py` — Pluggable backend:
- `disabled` (varsayilan, torch gerektirmez)
- `finbert` (yerel FinBERT transformer)
- `fingpt` (uzak FinGPT AWS endpoint)
