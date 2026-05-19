/// Remote Mode toggle — kullanıcı backend'i mi yoksa eski local Gemini'yi mi
/// kullanacağına SharedPreferences ile karar verir.
///
/// Phase B: opt-in remote mode (default false, mevcut lib.zip akışı sürer)
/// Phase C: default true (eski Dart Gemini kodu emekliye ayrılır)
/// Phase D: lib.zip'teki PromptBuilder, GeminiClient, IndicatorCalculator silinir
library;

import 'package:shared_preferences/shared_preferences.dart';

class RemoteMode {
  static const _key = 'finllm_remote_mode_enabled';
  static const _backendUrlKey = 'finllm_backend_url';
  static const _bearerKey = 'finllm_bearer_token';

  /// Default backend URL — geliştirme için localhost, prod'da Vercel/Render
  static const String defaultBackendUrl = 'http://10.0.2.2:8000';
  // Android emulator için 10.0.2.2 = host machine
  // iOS simulator için 127.0.0.1, gerçek cihaz için domain

  static Future<bool> isEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_key) ?? false;
  }

  static Future<void> setEnabled(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_key, enabled);
  }

  static Future<String> getBackendUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_backendUrlKey) ?? defaultBackendUrl;
  }

  static Future<void> setBackendUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_backendUrlKey, url);
  }

  static Future<String?> getBearerToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_bearerKey);
  }

  static Future<void> setBearerToken(String? token) async {
    final prefs = await SharedPreferences.getInstance();
    if (token == null || token.isEmpty) {
      await prefs.remove(_bearerKey);
    } else {
      await prefs.setString(_bearerKey, token);
    }
  }
}
