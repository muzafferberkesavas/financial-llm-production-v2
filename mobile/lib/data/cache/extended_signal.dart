/// ExtendedSignal — backend Phase 2.5 API kontratının Dart tarafı.
///
/// JSON schema:
///   backend/src/finllm/pipeline/stage5_writer.py `_signal_to_dict()` çıktısı
library;

class ExtendedSignal {
  final String ticker;
  final String? name;
  final String? sector;
  final String market;
  final DateTime generatedAt;
  final String runId;
  final String signal;
  final double confidence;
  final double? calibratedProbability;
  final double? entryZoneLow;
  final double? entryZoneHigh;
  final double? stopLoss;
  final double? expectedReturnPct;
  final int? timeHorizonDays;
  final List<PriceScenario> scenarios;
  final double allocationWeight;
  final double allocationCash;
  final int confluenceScore;
  final String marketRegime;
  final String weeklyTrend;
  final int confirmationCount;
  final double? backtest30dReturnPct;
  final bool backtestGatePassed;
  final bool isActionable;
  final RationaleBlock rationale;
  final List<String> warningFlags;
  final bool unsourcedFlag;
  final String llmModel;
  final double llmCostUsd;

  ExtendedSignal({
    required this.ticker,
    this.name,
    this.sector,
    required this.market,
    required this.generatedAt,
    required this.runId,
    required this.signal,
    required this.confidence,
    this.calibratedProbability,
    this.entryZoneLow,
    this.entryZoneHigh,
    this.stopLoss,
    this.expectedReturnPct,
    this.timeHorizonDays,
    required this.scenarios,
    required this.allocationWeight,
    required this.allocationCash,
    required this.confluenceScore,
    required this.marketRegime,
    required this.weeklyTrend,
    required this.confirmationCount,
    this.backtest30dReturnPct,
    required this.backtestGatePassed,
    required this.isActionable,
    required this.rationale,
    required this.warningFlags,
    required this.unsourcedFlag,
    required this.llmModel,
    required this.llmCostUsd,
  });

  factory ExtendedSignal.fromJson(Map<String, dynamic> json) {
    return ExtendedSignal(
      ticker: json['ticker'] as String,
      name: json['name'] as String?,
      sector: json['sector'] as String?,
      market: json['market'] as String,
      generatedAt: DateTime.parse(json['generated_at'] as String),
      runId: json['run_id'] as String? ?? '',
      signal: json['signal'] as String,
      confidence: (json['confidence'] as num).toDouble(),
      calibratedProbability: (json['calibrated_probability'] as num?)?.toDouble(),
      entryZoneLow: (json['entry_zone_low'] as num?)?.toDouble(),
      entryZoneHigh: (json['entry_zone_high'] as num?)?.toDouble(),
      stopLoss: (json['stop_loss'] as num?)?.toDouble(),
      expectedReturnPct: (json['expected_return_pct'] as num?)?.toDouble(),
      timeHorizonDays: json['time_horizon_days'] as int?,
      scenarios: (json['scenarios'] as List? ?? [])
          .map((s) => PriceScenario.fromJson(s as Map<String, dynamic>))
          .toList(),
      allocationWeight: ((json['allocation_weight'] as num?) ?? 0).toDouble(),
      allocationCash: ((json['allocation_cash'] as num?) ?? 0).toDouble(),
      confluenceScore: (json['confluence_score'] as num?)?.toInt() ?? 0,
      marketRegime: json['market_regime'] as String? ?? '',
      weeklyTrend: json['weekly_trend'] as String? ?? '',
      confirmationCount: (json['confirmation_count'] as num?)?.toInt() ?? 0,
      backtest30dReturnPct: (json['backtest_30d_return_pct'] as num?)?.toDouble(),
      backtestGatePassed: json['backtest_gate_passed'] as bool? ?? false,
      isActionable: json['is_actionable'] as bool? ?? false,
      rationale: RationaleBlock.fromJson(
          (json['rationale'] as Map<String, dynamic>?) ?? {}),
      warningFlags: (json['warning_flags'] as List? ?? []).cast<String>(),
      unsourcedFlag: json['unsourced_flag'] as bool? ?? false,
      llmModel: json['llm_model'] as String? ?? '',
      llmCostUsd: ((json['llm_cost_usd'] as num?) ?? 0).toDouble(),
    );
  }
}

class PriceScenario {
  final String label;
  final double targetPrice;
  final double probability;
  final double expectedReturnPct;

  PriceScenario({
    required this.label,
    required this.targetPrice,
    required this.probability,
    required this.expectedReturnPct,
  });

  factory PriceScenario.fromJson(Map<String, dynamic> json) => PriceScenario(
        label: json['label'] as String,
        targetPrice: (json['target_price'] as num).toDouble(),
        probability: (json['probability'] as num).toDouble(),
        expectedReturnPct: (json['expected_return_pct'] as num).toDouble(),
      );
}

class RationaleBlock {
  final String trend;
  final String formation;
  final String volume;
  final String news;
  final String fibonacci;
  final List<String> risks;
  final String full;

  RationaleBlock({
    required this.trend,
    required this.formation,
    required this.volume,
    required this.news,
    required this.fibonacci,
    required this.risks,
    required this.full,
  });

  factory RationaleBlock.fromJson(Map<String, dynamic> json) => RationaleBlock(
        trend: json['trend'] as String? ?? '',
        formation: json['formation'] as String? ?? '',
        volume: json['volume'] as String? ?? '',
        news: json['news'] as String? ?? '',
        fibonacci: json['fibonacci'] as String? ?? '',
        risks: (json['risks'] as List? ?? []).cast<String>(),
        full: json['full'] as String? ?? '',
      );
}

class SignalsResponse {
  final Map<String, dynamic> summary;
  final List<ExtendedSignal> signals;

  SignalsResponse({required this.summary, required this.signals});

  factory SignalsResponse.fromJson(Map<String, dynamic> json) => SignalsResponse(
        summary: json['summary'] as Map<String, dynamic>,
        signals: (json['signals'] as List)
            .map((s) => ExtendedSignal.fromJson(s as Map<String, dynamic>))
            .toList(),
      );
}

class PortfolioPosition {
  final String ticker;
  final String name;
  final String sector;
  final String signal;
  final double confidence;
  final double? calibratedProbability;
  final double allocationWeight;
  final double allocationCash;
  final double? expectedReturnPct;
  final int? timeHorizonDays;
  final double? entryZoneLow;
  final double? entryZoneHigh;
  final double? stopLoss;

  PortfolioPosition({
    required this.ticker,
    required this.name,
    required this.sector,
    required this.signal,
    required this.confidence,
    this.calibratedProbability,
    required this.allocationWeight,
    required this.allocationCash,
    this.expectedReturnPct,
    this.timeHorizonDays,
    this.entryZoneLow,
    this.entryZoneHigh,
    this.stopLoss,
  });

  factory PortfolioPosition.fromJson(Map<String, dynamic> json) => PortfolioPosition(
        ticker: json['ticker'] as String,
        name: json['name'] as String? ?? '',
        sector: json['sector'] as String? ?? '',
        signal: json['signal'] as String,
        confidence: (json['confidence'] as num).toDouble(),
        calibratedProbability:
            (json['calibrated_probability'] as num?)?.toDouble(),
        allocationWeight: (json['allocation_weight'] as num).toDouble(),
        allocationCash: (json['allocation_cash'] as num).toDouble(),
        expectedReturnPct: (json['expected_return_pct'] as num?)?.toDouble(),
        timeHorizonDays: json['time_horizon_days'] as int?,
        entryZoneLow: (json['entry_zone_low'] as num?)?.toDouble(),
        entryZoneHigh: (json['entry_zone_high'] as num?)?.toDouble(),
        stopLoss: (json['stop_loss'] as num?)?.toDouble(),
      );
}

class PortfolioResponse {
  final String market;
  final String runId;
  final DateTime asOf;
  final double totalCapital;
  final double cashBufferPct;
  final int allocatedCount;
  final double allocatedTotal;
  final double cashRemaining;
  final List<PortfolioPosition> positions;

  PortfolioResponse({
    required this.market,
    required this.runId,
    required this.asOf,
    required this.totalCapital,
    required this.cashBufferPct,
    required this.allocatedCount,
    required this.allocatedTotal,
    required this.cashRemaining,
    required this.positions,
  });

  factory PortfolioResponse.fromJson(Map<String, dynamic> json) =>
      PortfolioResponse(
        market: json['market'] as String,
        runId: json['run_id'] as String,
        asOf: DateTime.parse(json['as_of'] as String),
        totalCapital: (json['total_capital'] as num).toDouble(),
        cashBufferPct: (json['cash_buffer_pct'] as num).toDouble(),
        allocatedCount: json['allocated_count'] as int,
        allocatedTotal: (json['allocated_total'] as num).toDouble(),
        cashRemaining: (json['cash_remaining'] as num).toDouble(),
        positions: (json['positions'] as List)
            .map((p) => PortfolioPosition.fromJson(p as Map<String, dynamic>))
            .toList(),
      );
}
