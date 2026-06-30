# Frontend'ler

Proje iki ayrı frontend icerir. Ikisi de backend API'ye baglanir.

## Dashboard (Next.js 16 + React 19)

**Konum:** `dashboard/`

### Tech Stack
- Next.js 16.2, React 19.2
- Tailwind CSS 4
- Recharts 3.8 (grafikler)
- Vercel AI SDK (`@ai-sdk/react`) — Claude streaming
- Zod 4.4 (sema dogrulama)
- Lenis (smooth scroll)

### Yapi
```
dashboard/src/
├── app/
│   ├── page.tsx              # Marketing anasayfa (hero, problem, pillar, pipeline, CTA)
│   ├── app/                  # Uygulama route'lari
│   └── api/                  # API route'lar (backend proxy)
├── components/
│   ├── signal-card.tsx       # Sinyal karti
│   └── signal-card-v2.tsx    # Gelistirilmis sinyal karti
├── lib/
│   └── mock-signals.ts      # Mock veri (gercek API entegrasyonu bekliyor)
└── marketing/                # Pazarlama komponentleri (navbar, footer, sectionlar)
```

### Bilinen Durum
- Suanda **mock veri** gosteriyor (`lib/mock-signals.ts`)
- Gercek `/api/signals` cagrilarina gecis gerekiyor
- Portfolio UI sayfasi henuz yok

### CLAUDE.md Notu
`dashboard/CLAUDE.md` → `@AGENTS.md` referansi: Next.js 16 breaking change'leri icin `node_modules/next/dist/docs/` kontrol edilmeli.

## Vue Frontend (Vue 3 + Vite)

**Konum:** `frontend-vue/`

### Tech Stack
- Vue 3.5, Vite 6
- Pinia 2 (state management)
- ECharts 6 + vue-echarts 8 (gelismis grafikler)
- Tailwind CSS 4
- Vue Router 4

### Yapi
```
frontend-vue/src/
├── App.vue                   # Root component
├── views/                    # Sayfa gorunumleri (BIST sinyalleri, portfolio)
├── components/               # UI komponentleri
├── stores/                   # Pinia store'lar (global state)
└── router/                   # Vue Router yapilandirmasi
```

### Ozellikler
- Gercek zamanli grafik guncellemeleri (ECharts)
- Dogrudan backend API entegrasyonu
- BIST + emtia veri gosterimi
- Responsive Tailwind tasarim

## Yerel Gelistirme URL'leri

| Servis | URL |
|--------|-----|
| Backend API + Swagger | http://localhost:8000/docs |
| Dashboard (Next.js) | http://localhost:3000 |
| Vue Frontend | http://localhost:5173 |
