# docs/ - Proje Dokumantasyonu

Bu klasor projenin teknik dokumantasyonunu organize bir sekilde icerir. Her dosya bagimsiz bir konuyu kapsar.

## Dizin Yapisi

```
docs/
├── README.md                 # Bu dosya
├── architecture/
│   ├── overview.md           # Sistem mimarisi, 7-asamali pipeline
│   ├── pipeline-stages.md    # Her pipeline asamasinin detayi
│   └── domain-models.md      # Pydantic modeller, veri sözlesmesi
├── backend/
│   ├── api-endpoints.md      # REST API + WebSocket endpoint referansi
│   ├── llm-usage.md          # LLM model tiering, skills, maliyet
│   ├── database.md           # DuckDB/PostgreSQL sema, tablolar
│   └── scripts.md            # CLI scriptleri ve kullanim
├── frontend/
│   └── overview.md           # Dashboard (Next.js) + Vue frontend
├── config/
│   └── environment.md        # Env vars, API key'ler, runtime ayarlari
├── development/
│   ├── setup.md              # Kurulum, bagimlilıklar, yerel calistirma
│   ├── conventions.md        # Kodlama konvansiyonlari, tech stack
│   └── testing.md            # Test altyapisi, smoke test, backtest QA
└── deployment/
    └── production.md         # Docker, AWS, CI/CD, GitHub Actions
```
