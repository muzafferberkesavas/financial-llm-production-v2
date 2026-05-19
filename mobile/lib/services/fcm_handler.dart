/// Firebase Cloud Messaging handler — backend Stage 5'ten push notification.
///
/// Phase 2.7: stub (FCM kurulumu kullanıcının kendi Firebase projesini ister)
/// Phase 3: gerçek FCM topic subscribe + foreground/background handlers
///
/// Backend tarafında alerts/fcm_push.py eklenecek; mobile bu topic'lere abone:
///   - "signals_nasdaq_actionable"
///   - "signals_bist_actionable"
///   - "user_{uid}_watchlist_hit"
library;

import 'package:flutter/material.dart';

import '../data/cache/extended_signal.dart';

typedef SignalHandler = void Function(ExtendedSignal signal);

class FCMHandler {
  SignalHandler? onNewSignal;
  bool initialized = false;

  /// Initialize Firebase (Phase 3'te real implementation).
  /// Şu an no-op; gerçek call için firebase_messaging dependency lazım.
  Future<void> init({SignalHandler? handler}) async {
    onNewSignal = handler;
    // TODO Phase 3:
    //   - await Firebase.initializeApp()
    //   - permission iste (iOS için kritik)
    //   - FirebaseMessaging.instance.subscribeToTopic('signals_nasdaq_actionable')
    //   - FirebaseMessaging.onMessage.listen(...)
    initialized = true;
    debugPrint('[FCM] stub init (Phase 3\'te gerçekleştirilecek)');
  }

  /// Test çağrısı — Phase 2.7'de UI'de manual sinyal testlemek için
  void emitTestSignal(ExtendedSignal signal) {
    debugPrint('[FCM] test signal: ${signal.ticker} ${signal.signal}');
    onNewSignal?.call(signal);
  }
}

/// Global singleton — main.dart'tan init edilir
final fcmHandler = FCMHandler();
