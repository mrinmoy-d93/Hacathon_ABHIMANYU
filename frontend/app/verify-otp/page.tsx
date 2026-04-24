"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { Acronym, AcronymProvider } from "@/components/Acronym";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "@/components/ui/toast";
import { useSendOtp, useVerifyOtp } from "@/lib/hooks/useAuth";
import type { UserRole } from "@/lib/types";

/**
 * OTP verification screen — FRS FR-1.2, FR-1.5.
 *
 * - 6-digit auto-focus inputs with paste support.
 * - Admins include their police ID for 2FA (FR-1.2 / AC-11).
 * - Demo OTP hint shown for judges so they can log in without SMS.
 */
export default function VerifyOtpPage() {
  return (
    <AppShell>
      <AcronymProvider>
        <Suspense
          fallback={
            <div className="flex justify-center py-12 text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
            </div>
          }
        >
          <VerifyOtpInner />
        </Suspense>
      </AcronymProvider>
    </AppShell>
  );
}

function VerifyOtpInner() {
  const router = useRouter();
  const search = useSearchParams();
  const phone = search.get("phone") ?? "";
  const uiRole = (search.get("role") ?? "family") as string;
  const policeId = search.get("police_id") ?? undefined;

  const [digits, setDigits] = useState<string[]>(Array(6).fill(""));
  const [error, setError] = useState<string | null>(null);
  const inputsRef = useRef<Array<HTMLInputElement | null>>([]);
  const verify = useVerifyOtp();
  const resend = useSendOtp();

  useEffect(() => {
    inputsRef.current[0]?.focus();
  }, []);

  const submitCode = async (code: string) => {
    if (code.length !== 6) return;
    setError(null);
    try {
      const res = await verify.mutateAsync({
        phone,
        otp: code,
        police_id: policeId,
      });
      toast.success("Verified. Welcome to KHOJO.");
      router.push(landingFor(res.user.role));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Invalid code — please try again.";
      setError(message);
      toast.error(message);
      setDigits(Array(6).fill(""));
      inputsRef.current[0]?.focus();
    }
  };

  const handleChange = (index: number, raw: string) => {
    const clean = raw.replace(/\D/g, "");
    if (!clean) {
      setDigits((prev) => {
        const next = [...prev];
        next[index] = "";
        return next;
      });
      return;
    }

    // Paste support — if multiple digits pasted, spread across fields.
    if (clean.length > 1) {
      const pasted = clean.slice(0, 6 - index).split("");
      setDigits((prev) => {
        const next = [...prev];
        pasted.forEach((d, i) => (next[index + i] = d));
        return next;
      });
      const target = Math.min(index + pasted.length, 5);
      inputsRef.current[target]?.focus();
      if (index + pasted.length >= 6) {
        void submitCode([...digits].map((d, i) => pasted[i - index] ?? d).join("").slice(0, 6));
      }
      return;
    }

    setDigits((prev) => {
      const next = [...prev];
      next[index] = clean;
      if (index < 5) inputsRef.current[index + 1]?.focus();
      const assembled = next.join("");
      if (assembled.length === 6 && assembled.replace(/\D/g, "").length === 6) {
        void submitCode(assembled);
      }
      return next;
    });
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  const handleResend = async () => {
    if (!phone) return;
    try {
      await resend.mutateAsync({ phone });
      toast.success("New One-Time Password sent.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not resend code.");
    }
  };

  if (!phone) {
    return (
      <div className="mx-auto max-w-md">
        <Alert variant="destructive">
          <AlertTitle>Missing phone number</AlertTitle>
          <AlertDescription>
            Please start from the registration page.{" "}
            <Button variant="link" onClick={() => router.push("/register")} className="px-1">
              Go to register
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            Verify your phone
          </CardTitle>
          <CardDescription>
            We sent a 6-digit <Acronym short="OTP" /> to <strong>{phone}</strong>. Enter it below
            to finish signing in.
            {uiRole === "admin" && (
              <>
                {" "}
                As an administrator, we&apos;ll also match the government ID you provided (
                <Acronym short="2FA" />
                ).
              </>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Alert variant="info">
            <AlertTitle>Demo mode</AlertTitle>
            <AlertDescription>
              Use code <code className="rounded bg-secondary px-1.5 py-0.5 font-mono">123456</code>{" "}
              to verify during the demo.
            </AlertDescription>
          </Alert>

          <div
            className="flex justify-center gap-2"
            role="group"
            aria-label="One-Time Password digits"
          >
            {digits.map((digit, i) => (
              <input
                key={i}
                ref={(el) => {
                  inputsRef.current[i] = el;
                }}
                inputMode="numeric"
                maxLength={1}
                autoComplete={i === 0 ? "one-time-code" : "off"}
                className="h-12 w-10 rounded-md border border-input bg-background text-center text-xl font-semibold ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:h-14 sm:w-12 sm:text-2xl"
                value={digit}
                onChange={(e) => handleChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                aria-label={`Digit ${i + 1} of 6`}
              />
            ))}
          </div>

          {verify.isPending && (
            <p className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Verifying…
            </p>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertTitle>Could not verify</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="flex flex-col items-center gap-2 text-sm text-muted-foreground">
            <p>Code expires in 5 minutes.</p>
            <Button
              variant="link"
              onClick={handleResend}
              disabled={resend.isPending}
              className="h-auto p-0"
            >
              {resend.isPending ? "Resending…" : "Resend One-Time Password"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function landingFor(role: UserRole): string {
  switch (role) {
    case "field_worker":
      return "/field-worker/alerts";
    case "admin":
      return "/admin/overview";
    default:
      return "/cases/new/details";
  }
}
