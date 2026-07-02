import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { SafeSettings, SettingsPatch } from "../api/types";

// 백엔드 settings.json 이 단일 진실 공급원. react-query 로 캐시하고,
// 변경은 PUT 후 캐시를 갱신한다(로컬 단일 사용자라 단순하게).
export function useSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: api.settings,
    staleTime: Infinity,
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: SettingsPatch) => api.updateSettings(patch),
    onSuccess: (data: SafeSettings) => {
      qc.setQueryData(["settings"], data);
      // 키가 바뀌면(예: 토스 연동) 그 키에 의존하는 화면이 탭 전환 없이도
      // 최신 상태를 보여줘야 한다 — 탭이 언마운트되지 않는 구조라 쿼리가
      // 자동으로 다시 불리지 않으므로 명시적으로 무효화한다.
      void qc.invalidateQueries({ queryKey: ["toss-status"] });
    },
  });
}
