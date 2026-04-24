"use client";
/**
 * TanStack Query hooks for the /api/cases endpoints (FRS §6.2-6.3).
 *
 * useCaseResult polls every 2s while the pipeline is `processing`, then stops
 * once `complete` or `error` is seen (FRS §6.3 async pipeline).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { casesApi } from "../api";
import type {
  CaseCreate,
  CaseCreateResponse,
  CaseDetail,
  CaseResult,
  PhotoUploadResponse,
  ProcessResponse,
} from "../types";
import { queryKeys } from "./queryKeys";

export function useCreateCase() {
  const qc = useQueryClient();
  return useMutation<CaseCreateResponse, Error, CaseCreate>({
    mutationFn: (body) => casesApi.create(body),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: queryKeys.case(data.case_id) });
    },
  });
}

export function useCase(caseId: string | undefined) {
  return useQuery<CaseDetail, Error>({
    queryKey: caseId ? queryKeys.case(caseId) : ["case", "pending"],
    queryFn: () => casesApi.get(caseId as string),
    enabled: Boolean(caseId),
  });
}

export function useUploadPhoto(caseId: string) {
  const qc = useQueryClient();
  return useMutation<PhotoUploadResponse, Error, { file: File; age_at_photo: number }>({
    mutationFn: ({ file, age_at_photo }) => casesApi.uploadPhoto(caseId, file, age_at_photo),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.case(caseId) });
    },
  });
}

export function useProcessCase(caseId: string) {
  const qc = useQueryClient();
  return useMutation<ProcessResponse, Error, void>({
    mutationFn: () => casesApi.process(caseId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.caseResult(caseId) });
    },
  });
}

/**
 * Polls `/api/cases/{id}/result` every 2s while processing.
 *
 * Returns the TanStack Query result — consumers can render `data.status`
 * directly (complete / processing / unknown / error).
 */
export function useCaseResult(caseId: string | undefined) {
  return useQuery<CaseResult, Error>({
    queryKey: caseId ? queryKeys.caseResult(caseId) : ["case", "result", "pending"],
    queryFn: () => casesApi.result(caseId as string),
    enabled: Boolean(caseId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "processing" || status === "unknown" ? 2000 : false;
    },
    refetchIntervalInBackground: false,
  });
}
