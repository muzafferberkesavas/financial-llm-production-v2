# FinLLM Mobile — Phase 2.7 Skeleton

Bu klasör mobile cutover'ın Phase B/C/D dağıtımı için temel taşları içerir.
Mevcut `lib.zip` (BIST Flutter app) hâlâ standalone çalışıyor; cutover plana göre:

## Cutover Stratejisi

| Phase | Mobile | Backend | Durum |
|---|---|---|---|
| **A** (mevcut) | lib.zip — kendi Gemini call'u | yeni v2 API canlı | ✅ |
| **B** (sırada) | `+remote_mode` toggle, API'den oku | aynı | ⏳ |
| **C** | default remote_mode=true | aynı | sonra |
| **D** | Dart IndicatorCalculator + PromptBuilder + GeminiClient silinir | aynı | sonra |

## Klasör İçeriği

```
mobile/lib/
├── api/finllm_client.dart       — v2 API client (http + JSON)
├── data/cache/
│   └── extended_signal.dart      — Dart ExtendedSignal modeli (backend kontratı)
└── services/
    ├── remote_mode.dart          — SharedPreferences toggle (default off)
    └── fcm_handler.dart          — FCM stub (Phase 3'te gerçek)
```

## Phase B'ye geçiş — lib.zip refactor adımları

1. **`lib.zip`'i extract**: `mobile/lib_original/` (mevcut Flutter app)
2. **Yeni dependency'ler**: `pubspec.yaml`'a ekle:
   ```yaml
   dependencies:
     http: ^1.1.0
     shared_preferences: ^2.2.0  # zaten var
   ```
3. **`app_state.dart`'ı genişlet**:
   ```dart
   import 'package:finllm/api/finllm_client.dart';
   import 'package:finllm/services/remote_mode.dart';

   class AppState extends ChangeNotifier {
     FinLLMClient? _api;
     bool _useRemote = false;

     Future<void> initRemote() async {
       _useRemote = await RemoteMode.isEnabled();
       if (_useRemote) {
         _api = FinLLMClient(
           baseUrl: await RemoteMode.getBackendUrl(),
           bearerToken: await RemoteMode.getBearerToken(),
         );
       }
     }

     Future<void> _runGeminiAnalysis(...) async {
       if (_useRemote && _api != null) {
         // Backend'den çek, local Gemini bypass
         final resp = await _api!.getLatestSignals(market: 'bist');
         // ExtendedSignal'leri eski AiAnalysis schema'sına dönüştür
         for (final sig in resp.signals) {
           await _analysisRepo.saveAiAnalysis(
             AiAnalysis(
               stockId: ...,
               signal: sig.signal,
               confidence: sig.confidence,
               summary: sig.rationale.full,
               ...
             ),
           );
         }
       } else {
         // Eski lib.zip akışı (mevcut local Gemini)
         ...
       }
     }
   }
   ```
4. **Settings ekranına toggle ekle**:
   ```dart
   ListTile(
     title: const Text('Remote Mode (Beta)'),
     subtitle: const Text('Backend\'den sinyal çek'),
     trailing: Switch(
       value: state.useRemote,
       onChanged: (v) async {
         await RemoteMode.setEnabled(v);
         state.useRemote = v;
         state.notifyListeners();
       },
     ),
   ),
   ListTile(
     title: const Text('Backend URL'),
     subtitle: Text(state.backendUrl),
     onTap: () => _showUrlDialog(context),
   ),
   ```

## Backend URL ayarı (development)

- **Android emulator**: `http://10.0.2.2:8000` (host machine = 10.0.2.2)
- **iOS simulator**: `http://127.0.0.1:8000`
- **Gerçek cihaz** (aynı WiFi): `http://<bilgisayar_lan_ip>:8000`
- **Production**: `https://your-vercel-deployment.vercel.app`

## Phase D'de silinecek (lib.zip içindeki)

- `lib/ai/gemini_client.dart` — backend Stage 3 yapıyor
- `lib/ai/prompt_builder.dart` — backend skill kütüphanesinde
- `lib/ai/response_parser.dart` — backend response_parser (Claude tool calling)
- `lib/ai/news_translation_service.dart` — backend news/translator.py
- `lib/domain/analysis/indicator_calculator.dart` — backend indicators/core.py
- `lib/domain/analysis/fibonacci_calculator.dart` — backend indicators/fibonacci.py
- `lib/domain/filter/filter_pipeline.dart` — backend pipeline/stage1_filter.py

Kalan: sadece UI, local cache (signals'i offline görüntülemek için),
FCM handler, settings.

## Test

```bash
# Backend çalışsın
cd ../backend && python scripts/run_api.py --port 8000

# Mobile cihazda Settings → Remote Mode AÇIK
# Settings → Backend URL = http://10.0.2.2:8000
# Refresh → app artık backend'den sinyal çekiyor
```
