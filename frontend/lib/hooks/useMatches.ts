"use client";
/** TanStack Query hooks for /api/matches (FRS §6.5, FR-5.1–FR-5.5). */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { matchesApi } from "../api";
import type {
  ConfirmMatchResponse,
  NotMatchResponse,
  PendingMatch,
} from "../types";
import { queryKeys } from "./queryKeys";

export function usePendingMatches() {
  return useQuery<PendingMatch[], Error>({
    queryKey: queryKeys.pendingMatches,
    queryFn: () => matchesApi.pending(),
  });
}

export function useConfirmMatch() {
  const qc = useQueryClient();
  return useMutation<ConfirmMatchResponse, Error, { matchId: string }>({
    mutationFn: ({ matchId }) => matchesApi.confirm(matchId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.pendingMatches });
    },
  });
}

export function useNotMatch() {
  const qc = useQueryClient();
  return useMutation<NotMatchResponse, Error, { matchId: string; realPhoto: File }>({
    mutationFn: ({ matchId, realPhoto }) => matchesApi.notMatch(matchId, realPhoto),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.pendingMatches });
    },
  });
}
