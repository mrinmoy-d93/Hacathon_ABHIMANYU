"use client";
/** /health liveness probe with a 30s refetch interval (FRS NFR-2). */
import { useQuery } from "@tanstack/react-query";

import { healthApi } from "../api";
import type { HealthResponse } from "../types";
import { queryKeys } from "./queryKeys";

export function useHealth() {
  return useQuery<HealthResponse, Error>({
    queryKey: queryKeys.health,
    queryFn: () => healthApi.get(),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}
