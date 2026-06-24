// 백엔드 DataEnvelope 계약(camelCase)과 1:1 대응한다.

export type DataStatus =
  | "LIVE"
  | "DELAYED"
  | "STALE"
  | "NO_DATA"
  | "NEEDS_KEY"
  | "RATE_LIMITED"
  | "ERROR";

export interface DataEnvelope<T> {
  data: T | null;
  status: DataStatus;
  source: string;
  asOf: string | null;
  delayMinutes: number | null;
  message: string | null;
}

export interface Quote {
  symbol: string;
  price: number;
  change: number | null;
  changePct: number | null;
  currency: string | null;
  name: string | null;
}

export interface Bar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

export interface IndicatorSeries {
  ma: Record<string, (number | null)[]>;
  bbUpper: (number | null)[];
  bbMiddle: (number | null)[];
  bbLower: (number | null)[];
  rsi: (number | null)[];
  macd: (number | null)[];
  macdSignal: (number | null)[];
  macdHist: (number | null)[];
}

export interface ChartData {
  symbol: string;
  period: string;
  interval: string;
  bars: Bar[];
  indicators: IndicatorSeries;
}

export interface StripItem {
  label: string;
  symbol: string;
  quote: DataEnvelope<Quote>;
}

export interface Plan {
  style: string; // dca | lump
  monthlyContribution: number;
  rules: string[];
  horizonYears: number;
  note: string;
}

export interface DashboardLayout {
  left: string[];
  right: string[];
  hidden: string[];
}

export interface SafeSettings {
  watchlist: string[];
  defaultSymbol: string;
  apiKeys: Record<string, boolean>;
  ai: { backend: string; model: string; beginnerMode: boolean };
  ui: {
    theme: string;
    density: string;
    upColor: string;
    defaultPeriod: string;
    baseCurrency?: string;
  };
  plan: Plan;
  dashboard: DashboardLayout;
}

// 설정 부분 업데이트(PUT /api/settings) — 백엔드가 필드별로 병합한다.
export interface SettingsPatch {
  watchlist?: string[];
  defaultSymbol?: string;
  apiKeys?: Record<string, string>;
  ai?: Record<string, unknown>;
  ui?: Record<string, unknown>;
  plan?: Record<string, unknown>;
  dashboard?: DashboardLayout;
}

export type Sentiment = "POSITIVE" | "NEUTRAL" | "NEGATIVE";
export type Importance = "HIGH" | "MEDIUM" | "LOW";

export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  publisher: string | null;
  link: string | null;
  published: string | null;
  tickers: string[];
}

export interface NewsAnalysis {
  sentiment: Sentiment;
  importance: Importance;
  tickers: string[];
  koreanSummary: string;
}

export interface AnalyzedNews {
  item: NewsItem;
  analysis: NewsAnalysis;
}

export interface NewsSummaryResult {
  backend: string; // ollama | gemini | rule | none
  items: AnalyzedNews[];
}

export interface AskResult {
  backend: string;
  answer: string;
}

export interface Filing {
  form: string;
  title: string;
  filed: string;
  reportDate: string | null;
  url: string;
  accession: string;
}

export interface FilingList {
  entity: string;
  cik: string | null;
  market: string; // US | KR
  filings: Filing[];
}

// ── 포트폴리오 ─────────────────────────────────────────────────────
export interface Position {
  symbol: string;
  quantity: number;
  avgCost: number;
}

export interface PositionValuation {
  symbol: string;
  quantity: number;
  avgCost: number;
  costBasis: number;
  name: string | null;
  currency: string | null;
  price: number | null;
  marketValue: number | null;
  unrealizedPnl: number | null;
  unrealizedPnlPct: number | null;
  weight: number | null;
  realizedPnl: number;
  status: DataStatus;
}

export interface PortfolioSummary {
  positions: PositionValuation[];
  totalValue: number;
  totalCost: number;
  totalPnl: number;
  totalPnlPct: number | null;
  valuedCount: number;
  unvaluedCount: number;
  asOf: string | null;
  totalRealized: number;
  valueKrw: number | null;
  valueUsd: number | null;
  unrealizedKrw: number | null;
  unrealizedUsd: number | null;
  realizedKrw: number | null;
  realizedUsd: number | null;
  fxRate: number | null;
  fxStatus: DataStatus;
}

export interface Transaction {
  id: string;
  date: string | null;
  type: "buy" | "sell";
  symbol: string;
  quantity: number;
  price: number;
  currency: string;
}

// ── 안심 레이어 ─────────────────────────────────────────────────────
export interface DrawdownContext {
  symbol: string;
  status: DataStatus;
  asOf: string | null;
  assetType: string | null;
  currentPrice: number | null;
  peakPrice: number | null;
  peakDate: string | null;
  currentDrawdownPct: number | null;
  historyYears: number | null;
  thresholdPct: number | null;
  comparableCount: number;
  recoveredCount: number;
  medianRecoveryDays: number | null;
  maxRecoveryDays: number | null;
  worstDrawdownPct: number | null;
  limitedHistory: boolean;
  note: string | null;
  message: string | null;
}

export type VerdictTone = "ON_TRACK" | "NORMAL_DIP" | "UNUSUAL" | "NO_HOLDINGS";

export interface HomeVerdict {
  tone: VerdictTone;
  headline: string;
  subline: string;
  todo: string;
  totalValue: number;
  totalPnlPct: number | null;
  context: DrawdownContext | null;
  asOf: string | null;
}

export interface SymbolMatch {
  symbol: string;
  name: string;
  type: string; // EQUITY | ETF | INDEX | MUTUALFUND
  exchange: string | null;
}

export interface CalendarEvent {
  symbol: string;
  type: string; // earnings | exDividend
  date: string; // YYYY-MM-DD
}

export interface Holding {
  symbol: string | null;
  name: string;
  weight: number; // %
}

export interface Fundamentals {
  symbol: string;
  status: DataStatus;
  name: string | null;
  type: string | null; // EQUITY | ETF
  summary: string | null;
  sector: string | null;
  industry: string | null;
  category: string | null;
  currency: string | null;
  marketCap: number | null;
  totalAssets: number | null;
  peRatio: number | null;
  dividendYield: number | null;
  week52High: number | null;
  week52Low: number | null;
  beta: number | null;
  topHoldings: Holding[];
  message: string | null;
}

// ── 근거 패널 (Decision Briefing) ────────────────────────────────────
export interface MacroMetric {
  label: string;
  value: number | null;
  unit: string | null;
  asOf: string | null;
  change: number | null;
  status: DataStatus;
  source: string;
  note: string | null;
}

export interface IndexTrend {
  label: string;
  symbol: string;
  price: number | null;
  vsMa50Pct: number | null;
  vsMa200Pct: number | null;
  status: DataStatus;
}

export interface MacroConditions {
  rate: MacroMetric;
  cpi: MacroMetric;
  indices: IndexTrend[];
  asOf: string | null;
}

export interface HoldingWeight {
  symbol: string;
  weight: number;
}

export interface CorrelationPair {
  a: string;
  b: string;
  corr: number;
}

export interface PortfolioRisk {
  status: DataStatus;
  asOf: string | null;
  concentrationHhi: number | null;
  topSymbol: string | null;
  topWeight: number | null;
  weights: HoldingWeight[];
  correlations: CorrelationPair[];
  avgCorrelation: number | null;
  lookbackDays: number | null;
  excluded: string[];
  message: string | null;
}

export interface ValuationContext {
  symbol: string;
  status: DataStatus;
  asOf: string | null;
  peRatio: number | null;
  pe5YAvg: number | null;
  peVs5YAvgPct: number | null;
  dividendYield: number | null;
  week52High: number | null;
  week52Low: number | null;
  week52PositionPct: number | null;
  price: number | null;
  vsMa200Pct: number | null;
  note: string | null;
  message: string | null;
}

export const PERIODS = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y"] as const;
export const INTERVALS = ["1D", "1W", "1M"] as const;
export type Period = (typeof PERIODS)[number];
export type Interval = (typeof INTERVALS)[number];
