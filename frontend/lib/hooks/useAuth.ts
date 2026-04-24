"use client";
/**
 * TanStack Query hooks for the /api/auth endpoints (FRS §7.1).
 *
 * useVerifyOtp writes the returned JWT into the Zustand auth store on success
 * so subsequent requests attach the Authorization header automatically.
 */
import { useMutation } from "@tanstack/react-query";

import { authApi } from "../api";
import { useAuthStore } from "../authStore";
import type {
  RegisterRequest,
  RegisterResponse,
  SendOtpRequest,
  SendOtpResponse,
  VerifyOtpRequest,
  VerifyOtpResponse,
} from "../types";

export function useRegister() {
  return useMutation<RegisterResponse, Error, RegisterRequest>({
    mutationFn: (body) => authApi.register(body),
  });
}

export function useSendOtp() {
  return useMutation<SendOtpResponse, Error, SendOtpRequest>({
    mutationFn: (body) => authApi.sendOtp(body),
  });
}

export function useVerifyOtp() {
  const setSession = useAuthStore((s) => s.setSession);
  return useMutation<VerifyOtpResponse, Error, VerifyOtpRequest>({
    mutationFn: (body) => authApi.verifyOtp(body),
    onSuccess: (data) => {
      setSession({ token: data.access_token, user: data.user, expiresIn: data.expires_in });
    },
  });
}

export function useLogout() {
  const clearSession = useAuthStore((s) => s.clearSession);
  return () => clearSession();
}
