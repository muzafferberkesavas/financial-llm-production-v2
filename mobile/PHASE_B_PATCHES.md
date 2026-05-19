# Phase B — lib.zip refactor patches

Concrete Dart kod yamaları. Bu yamaları uygulayarak `lib.zip` mobile uygulaman:
1. Remote mode toggle gösterir
2. Backend API'den sinyal çekebilir
3. Eski local Gemini akışını opt-in tutar

## Adım 0 — Dependency ekle

`pubspec.yaml` (lib.zip'in extract'inde mevcut Flutter projende):

```yaml
dependencies:
  flutter:
    sdk: flutter
  # ... mevcut
  http: ^1.1.0                # YENI: backend API çağrısı için
  # shared_preferences zaten var
```

`flutter pub get` koş.

## Adım 1 — API client + ExtendedSignal modelini kopyala

`mobile/lib/api/` ve `mobile/lib/data/cache/` ve `mobile/lib/services/` klasörlerinin içeriğini
projendeki `lib/` altına olduğu gibi kopyala:

```
lib/
├── api/
│   └── finllm_client.dart       (yeni)
├── data/
│   └── cache/
│       └── extended_signal.dart (yeni)
├── services/
│   ├── remote_mode.dart          (yeni)
│   └── fcm_handler.dart          (yeni — Phase 3+)
└── (lib.zip'in mevcut klasörleri)
```

## Adım 2 — Settings ekranına Remote Mode toggle ekle

`lib/ui/screens/settings_screen.dart` (`SettingsScreen`'in build'inin sonuna):

```dart
import 'package:finllm/services/remote_mode.dart';
import 'package:finllm/api/finllm_client.dart';

// _SettingsScreenState içinde:
bool _useRemote = false;
String _backendUrl = RemoteMode.defaultBackendUrl;
String? _bearer;

@override
void initState() {
  super.initState();
  RemoteMode.isEnabled().then((v) => setState(() => _useRemote = v));
  RemoteMode.getBackendUrl().then((u) => setState(() => _backendUrl = u));
  RemoteMode.getBearerToken().then((b) => setState(() => _bearer = b));
}

// build()'in sonuna ekle (mevcut card'lardan sonra):
Card(
  child: Padding(
    padding: const EdgeInsets.all(16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Remote Mode (Beta)',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        const Text(
          'Backend\'den sinyal çek. Kapalıyken eski lokal Gemini akışı çalışır.',
          style: TextStyle(color: Colors.grey, fontSize: 12),
        ),
        const SizedBox(height: 12),
        SwitchListTile(
          title: const Text('Remote Mode'),
          subtitle: Text(_useRemote ? 'Backend aktif' : 'Local Gemini aktif'),
          value: _useRemote,
          onChanged: (v) async {
            await RemoteMode.setEnabled(v);
            setState(() => _useRemote = v);
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(
              content: Text(v
                  ? 'Remote mode AÇIK — yenilemede backend\'den çekecek'
                  : 'Local Gemini akışı geri döndü'),
            ));
          },
        ),
        const Divider(),
        ListTile(
          title: const Text('Backend URL'),
          subtitle: Text(_backendUrl),
          trailing: const Icon(Icons.edit, size: 18),
          onTap: () async {
            final controller = TextEditingController(text: _backendUrl);
            final result = await showDialog<String>(
              context: context,
              builder: (_) => AlertDialog(
                title: const Text('Backend URL'),
                content: TextField(
                  controller: controller,
                  decoration: const InputDecoration(
                    hintText: 'http://10.0.2.2:8000',
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('İptal'),
                  ),
                  ElevatedButton(
                    onPressed: () => Navigator.pop(context, controller.text),
                    child: const Text('Kaydet'),
                  ),
                ],
              ),
            );
            if (result != null && result.isNotEmpty) {
              await RemoteMode.setBackendUrl(result);
              setState(() => _backendUrl = result);
            }
          },
        ),
        ListTile(
          title: const Text('Bearer Token'),
          subtitle: Text(
            _bearer == null ? '(yok — anonim erişim)' : '••••${_bearer!.substring(_bearer!.length - 4)}',
          ),
          trailing: const Icon(Icons.edit, size: 18),
          onTap: () async {
            final controller = TextEditingController(text: _bearer);
            final result = await showDialog<String?>(
              context: context,
              builder: (_) => AlertDialog(
                title: const Text('API Bearer Token'),
                content: TextField(
                  controller: controller,
                  obscureText: true,
                  decoration: const InputDecoration(
                    hintText: 'Boş bırakırsan anonim',
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context, null),
                    child: const Text('İptal'),
                  ),
                  ElevatedButton(
                    onPressed: () => Navigator.pop(context, controller.text),
                    child: const Text('Kaydet'),
                  ),
                ],
              ),
            );
            if (result != null) {
              await RemoteMode.setBearerToken(result.isEmpty ? null : result);
              setState(() => _bearer = result.isEmpty ? null : result);
            }
          },
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: () async {
            try {
              final api = FinLLMClient(
                baseUrl: await RemoteMode.getBackendUrl(),
                bearerToken: await RemoteMode.getBearerToken(),
              );
              final health = await api.health();
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                content: Text('✓ Backend OK: ${health['version']}'),
              ));
              api.dispose();
            } catch (e) {
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                content: Text('❌ Backend hatası: $e'),
                backgroundColor: Colors.red,
              ));
            }
          },
          icon: const Icon(Icons.network_check),
          label: const Text('Bağlantı Test Et'),
        ),
      ],
    ),
  ),
),
```

## Adım 3 — AppState'e remote fetch path ekle

`lib/ui/providers/app_state.dart`:

```dart
import 'package:finllm/api/finllm_client.dart';
import 'package:finllm/services/remote_mode.dart';

class AppState extends ChangeNotifier {
  // ... mevcut alanlar ...
  FinLLMClient? _api;
  bool _useRemote = false;

  Future<void> _ensureApiClient() async {
    _useRemote = await RemoteMode.isEnabled();
    if (_useRemote && _api == null) {
      _api = FinLLMClient(
        baseUrl: await RemoteMode.getBackendUrl(),
        bearerToken: await RemoteMode.getBearerToken(),
      );
    } else if (!_useRemote && _api != null) {
      _api!.dispose();
      _api = null;
    }
  }

  Future<void> runManualAnalysis() async {
    await _ensureApiClient();

    if (_useRemote && _api != null) {
      // Phase B: backend'den çek, local Gemini bypass
      try {
        progressMessage = 'Backend\'den sinyaller çekiliyor...';
        isLoading = true;
        notifyListeners();

        final resp = await _api!.getLatestSignals(market: 'bist');
        // ExtendedSignal'leri AiAnalysis schema'sına dönüştür
        for (final sig in resp.signals) {
          // Stock ID'yi DB'den al
          final stock = allStocks.firstWhere(
            (s) => s.ticker == sig.ticker,
            orElse: () => Stock(ticker: sig.ticker, name: sig.name ?? sig.ticker),
          );
          if (stock.id == null) continue;

          await _analysisRepo.saveAiAnalysis(AiAnalysis(
            stockId: stock.id!,
            datetime: sig.generatedAt.millisecondsSinceEpoch,
            analysisType: 'GUNLUK_REMOTE',
            summary: sig.rationale.full,
            signal: sig.signal,
            confidence: sig.confidence,
            riskReward: sig.scenarios.isNotEmpty
                ? '${sig.scenarios.first.expectedReturnPct}% / ${sig.stopLoss}'
                : null,
            scenarioStatus: 'REMOTE',
            rawResponse: 'Remote signal from backend run ${sig.runId}',
          ));
        }
        await loadRecentAnalyses();
        await _updatePortfolioFromAnalysis();
        lastUpdatedTime = DateFormat('HH:mm').format(DateTime.now());
        _persistState();
      } catch (e) {
        lastError = 'Backend hatası: $e';
      } finally {
        isLoading = false;
        progressMessage = null;
        notifyListeners();
      }
      return;
    }

    // Local mode (mevcut akış) — değişmez
    // ... lib.zip'in mevcut runManualAnalysis kodu ...
  }
}
```

## Adım 4 — Test akışı

1. Backend'i yerel başlat:
   ```bash
   cd backend && python scripts/run_api.py --port 8000
   ```

2. Bir pipeline run yap (BIST için):
   ```bash
   python scripts/run_funnel.py --market bist --llm claude
   ```

3. Mobile cihazda (emulator):
   - Settings → Remote Mode AÇIK
   - Backend URL = `http://10.0.2.2:8000` (Android emulator)
   - "Bağlantı Test Et" → ✓ Backend OK
   - Ana sayfa → Analiz Et → backend'den sinyal çekecek

## Adım 5 — Phase C için kaldırılacaklar (sonra)

Remote mode default açıldıktan sonra Dart kodundan silinecek dosyalar:
- `lib/ai/gemini_client.dart`
- `lib/ai/prompt_builder.dart`
- `lib/ai/response_parser.dart`
- `lib/ai/news_translation_service.dart`
- `lib/domain/analysis/indicator_calculator.dart`
- `lib/domain/analysis/fibonacci_calculator.dart`
- `lib/domain/filter/filter_pipeline.dart`

Sadece UI + local cache + API client kalır → mobile boyutu küçülür.
