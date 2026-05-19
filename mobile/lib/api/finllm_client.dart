/// FinLLM v2 API Client — backend/src/finllm/api/main.py'ye HTTP bağlanır.
///
/// Phase B (remote mode) için: Flutter app artık kendi Gemini call'unu yapmayacak,
/// sinyalleri backend'den çekecek.
///
/// Endpoints:
///   GET /v2/signals/latest?market=bist|nasdaq
///   GET /v2/signals/by-ticker/{ticker}
///   GET /v2/portfolio/{market}
///   GET /v2/portfolio/
///   GET /v2/history/calibration
///   GET /v2/history/outcomes
///   GET /v2/watchlist/{user_id}
///   POST /v2/watchlist/{user_id}/add|remove
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import '../data/cache/extended_signal.dart';

class FinLLMClient {
  final String baseUrl;
  final String? bearerToken;
  final http.Client _client;

  FinLLMClient({
    required this.baseUrl,
    this.bearerToken,
    http.Client? client,
  }) : _client = client ?? http.Client();

  Map<String, String> get _headers => {
        'Accept': 'application/json',
        if (bearerToken != null) 'Authorization': 'Bearer $bearerToken',
      };

  Uri _uri(String path, [Map<String, String>? query]) {
    final base = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    return Uri.parse('$base$path').replace(queryParameters: query);
  }

  Future<Map<String, dynamic>> _getJson(Uri uri) async {
    final resp = await _client.get(uri, headers: _headers).timeout(
          const Duration(seconds: 20),
        );
    if (resp.statusCode != 200) {
      throw FinLLMApiException(
        'API ${uri.path}: ${resp.statusCode}',
        statusCode: resp.statusCode,
        body: resp.body,
      );
    }
    return jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
  }

  /// Health check
  Future<Map<String, dynamic>> health() async {
    return _getJson(_uri('/v2/health'));
  }

  /// En son sinyaller (market spesifik)
  Future<SignalsResponse> getLatestSignals({
    String market = 'nasdaq',
    bool actionableOnly = false,
  }) async {
    final data = await _getJson(_uri('/v2/signals/latest', {
      'market': market,
      if (actionableOnly) 'actionable_only': 'true',
    }));
    return SignalsResponse.fromJson(data);
  }

  /// Tek ticker için son sinyali ara (son N run içinde)
  Future<({Map<String, dynamic> summary, ExtendedSignal signal})> getSignalByTicker(
    String ticker, {
    int lookback = 10,
  }) async {
    final data = await _getJson(_uri(
      '/v2/signals/by-ticker/${ticker.toUpperCase()}',
      {'lookback': lookback.toString()},
    ));
    return (
      summary: data['summary'] as Map<String, dynamic>,
      signal: ExtendedSignal.fromJson(data['signal'] as Map<String, dynamic>),
    );
  }

  /// Portföy (market spesifik)
  Future<PortfolioResponse> getPortfolio(String market) async {
    final data = await _getJson(_uri('/v2/portfolio/$market'));
    return PortfolioResponse.fromJson(data);
  }

  /// Watchlist
  Future<List<String>> getWatchlist(String userId) async {
    final data = await _getJson(_uri('/v2/watchlist/$userId'));
    return (data['tickers'] as List).cast<String>();
  }

  Future<List<String>> addToWatchlist(String userId, String ticker) async {
    final resp = await _client.post(
      _uri('/v2/watchlist/$userId/add'),
      headers: {..._headers, 'Content-Type': 'application/json'},
      body: jsonEncode({'ticker': ticker}),
    );
    if (resp.statusCode != 200) {
      throw FinLLMApiException('add watchlist: ${resp.statusCode}',
          statusCode: resp.statusCode, body: resp.body);
    }
    final data = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return (data['tickers'] as List).cast<String>();
  }

  Future<List<String>> removeFromWatchlist(String userId, String ticker) async {
    final resp = await _client.post(
      _uri('/v2/watchlist/$userId/remove'),
      headers: {..._headers, 'Content-Type': 'application/json'},
      body: jsonEncode({'ticker': ticker}),
    );
    if (resp.statusCode != 200) {
      throw FinLLMApiException('remove watchlist: ${resp.statusCode}',
          statusCode: resp.statusCode, body: resp.body);
    }
    final data = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return (data['tickers'] as List).cast<String>();
  }

  void dispose() {
    _client.close();
  }
}

class FinLLMApiException implements Exception {
  final String message;
  final int? statusCode;
  final String? body;

  FinLLMApiException(this.message, {this.statusCode, this.body});

  @override
  String toString() => 'FinLLMApiException($statusCode): $message';
}
