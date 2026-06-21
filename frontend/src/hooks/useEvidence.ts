import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

// 근거 ③ 거시: 천천히 변함 → 10분 staleTime
export function useMacroConditions() {
  return useQuery({
    queryKey: ["macroConditions"],
    queryFn: api.macroConditions,
    staleTime: 10 * 60_000,
  });
}

// 근거 ④ 포트폴리오 리스크: 보유/시세 기반 → 60초 refetch
export function usePortfolioRisk() {
  return useQuery({
    queryKey: ["portfolioRisk"],
    queryFn: api.portfolioRisk,
    refetchInterval: 60_000,
  });
}

// 근거 ① 밸류: 종목별, 천천히 변함 → 5분 staleTime
export function useValuation(symbol: string) {
  return useQuery({
    queryKey: ["valuation", symbol],
    queryFn: () => api.valuation(symbol),
    staleTime: 5 * 60_000,
  });
}
