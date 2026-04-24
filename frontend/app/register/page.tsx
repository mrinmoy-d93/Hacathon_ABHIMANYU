"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { Loader2, UserPlus } from "lucide-react";

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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "@/components/ui/toast";
import { useRegister, useSendOtp } from "@/lib/hooks/useAuth";

/**
 * UI roles shown to the user (FRS FR-1.1).
 *
 * The backend collapses "family" and "community" into a single role value
 * because both are ordinary case reporters; only the label differs in the UI.
 */
const UI_ROLES = ["family", "community", "field_worker", "admin"] as const;
type UiRole = (typeof UI_ROLES)[number];

const ROLE_LABEL: Record<UiRole, string> = {
  family: "Family member",
  community: "Community member",
  field_worker: "Field worker",
  admin: "Administrator (police / government)",
};

const schema = z
  .object({
    name: z.string().trim().min(2, "Please enter at least 2 characters."),
    phone: z
      .string()
      .trim()
      .regex(/^\d{10}$/, "Enter a 10-digit phone number, digits only."),
    location: z.string().trim().min(2, "Please enter your city or area."),
    role: z.enum(UI_ROLES),
    police_id: z.string().trim().optional(),
  })
  .refine((data) => data.role !== "admin" || (data.police_id && data.police_id.length >= 4), {
    path: ["police_id"],
    message: "Police / government identification is required for administrators.",
  });

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const router = useRouter();
  const registerMut = useRegister();
  const sendOtp = useSendOtp();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { role: "family" },
  });

  const role = watch("role");

  const onSubmit = async (data: FormValues) => {
    setSubmitError(null);
    try {
      // Backend only knows three roles — "community" is UI-only.
      const backendRole = data.role === "community" ? "family" : data.role;
      await registerMut.mutateAsync({
        name: data.name,
        phone: data.phone,
        location: data.location,
        role: backendRole,
      });
      await sendOtp.mutateAsync({ phone: data.phone });
      toast.success("Account created. Check your phone for the One-Time Password.");
      const qs = new URLSearchParams({ phone: data.phone, role: data.role });
      if (data.police_id) qs.set("police_id", data.police_id);
      router.push(`/verify-otp?${qs.toString()}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not register. Please try again.";
      setSubmitError(message);
      toast.error(message);
    }
  };

  return (
    <AppShell>
      <AcronymProvider>
        <div className="mx-auto max-w-xl">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-primary">
                <UserPlus className="h-5 w-5" aria-hidden="true" />
                Create your KHOJO account
              </CardTitle>
              <CardDescription>
                We&apos;ll send a 6-digit <Acronym short="OTP" /> to the phone number you provide.
                Administrators additionally authenticate with a government identification number (
                <Acronym short="2FA" />
                ).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="name">Full name</Label>
                  <Input
                    id="name"
                    autoComplete="name"
                    aria-invalid={Boolean(errors.name)}
                    aria-describedby={errors.name ? "name-error" : undefined}
                    {...register("name")}
                  />
                  {errors.name && (
                    <p id="name-error" className="text-xs text-destructive">
                      {errors.name.message}
                    </p>
                  )}
                </div>

                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="phone">Mobile number</Label>
                  <Input
                    id="phone"
                    inputMode="numeric"
                    autoComplete="tel"
                    placeholder="10 digits, e.g. 9876543210"
                    aria-invalid={Boolean(errors.phone)}
                    aria-describedby={errors.phone ? "phone-error" : undefined}
                    {...register("phone")}
                  />
                  {errors.phone && (
                    <p id="phone-error" className="text-xs text-destructive">
                      {errors.phone.message}
                    </p>
                  )}
                </div>

                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="location">City or area</Label>
                  <Input
                    id="location"
                    autoComplete="address-level2"
                    placeholder="e.g. Ahmedabad"
                    aria-invalid={Boolean(errors.location)}
                    aria-describedby={errors.location ? "location-error" : undefined}
                    {...register("location")}
                  />
                  {errors.location && (
                    <p id="location-error" className="text-xs text-destructive">
                      {errors.location.message}
                    </p>
                  )}
                </div>

                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="role">I am a…</Label>
                  <Controller
                    control={control}
                    name="role"
                    render={({ field }) => (
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger id="role">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {UI_ROLES.map((r) => (
                            <SelectItem key={r} value={r}>
                              {ROLE_LABEL[r]}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                </div>

                {role === "admin" && (
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="police_id">
                      Police / government identification number
                    </Label>
                    <Input
                      id="police_id"
                      placeholder="e.g. GJPOL-42198"
                      aria-invalid={Boolean(errors.police_id)}
                      aria-describedby={errors.police_id ? "police-id-error" : "police-id-help"}
                      {...register("police_id")}
                    />
                    <p id="police-id-help" className="text-xs text-muted-foreground">
                      Required for administrator <Acronym short="2FA" /> per FRS FR-1.2.
                    </p>
                    {errors.police_id && (
                      <p id="police-id-error" className="text-xs text-destructive">
                        {errors.police_id.message}
                      </p>
                    )}
                  </div>
                )}

                {submitError && (
                  <Alert variant="destructive">
                    <AlertTitle>Something went wrong</AlertTitle>
                    <AlertDescription>{submitError}</AlertDescription>
                  </Alert>
                )}

                <Button
                  type="submit"
                  size="lg"
                  disabled={isSubmitting || registerMut.isPending || sendOtp.isPending}
                >
                  {(isSubmitting || registerMut.isPending || sendOtp.isPending) && (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  )}
                  Continue
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </AcronymProvider>
    </AppShell>
  );
}
