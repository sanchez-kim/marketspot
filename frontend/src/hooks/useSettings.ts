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
    onSuccess: (data: SafeSettings) => qc.setQueryData(["settings"], data),
  });
}
