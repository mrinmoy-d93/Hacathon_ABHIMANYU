"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { ArrowRight, FileText, Info, Loader2 } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { Acronym, AcronymProvider } from "@/components/Acronym";
import { AuthHydrationGuard } from "@/components/AuthHydrationGuard";
import { StepIndicator } from "@/components/StepIndicator";
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
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { useCreateCase } from "@/lib/hooks/useCases";

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: CURRENT_YEAR - 1990 + 1 }, (_, i) => CURRENT_YEAR - i);

const schema = z.object({
  person_name: z.string().trim().min(2, "Please enter the full name (at least 2 characters)."),
  year_missing: z
    .coerce.number()
    .int()
    .min(1990, "Earliest year supported is 1990.")
    .max(CURRENT_YEAR, "Year cannot be in the future."),
  age_at_disappearance: z
    .coerce.number()
    .int()
    .min(0, "Age cannot be negative.")
    .max(100, "Please enter an age below 100."),
  last_seen_location: z.string().trim().min(2, "Please enter the last-seen city or area."),
  identifying_marks: z.string().trim().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function NewCaseDetailsPage() {
  return (
    <AppShell>
      <AcronymProvider>
        <AuthHydrationGuard requiredRole={["family", "field_worker", "admin"]}>
          <DetailsForm />
        </AuthHydrationGuard>
      </AcronymProvider>
    </AppShell>
  );
}

function DetailsForm() {
  const router = useRouter();
  const create = useCreateCase();

  const {
    register,
    handleSubmit,
    watch,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      year_missing: CURRENT_YEAR - 5,
      age_at_disappearance: 5,
    },
  });

  const yearMissing = Number(watch("year_missing")) || 0;
  const ageAtDis = Number(watch("age_at_disappearance")) || 0;
  const predictedAge =
    yearMissing > 0 && ageAtDis >= 0
      ? ageAtDis + (CURRENT_YEAR - yearMissing)
      : null;

  const onSubmit = async (data: FormValues) => {
    try {
      const res = await create.mutateAsync({
        person_name: data.person_name,
        year_missing: data.year_missing,
        age_at_disappearance: data.age_at_disappearance,
        last_seen_location: data.last_seen_location,
        identifying_marks: data.identifying_marks || null,
      });
      toast.success(`Case created — ${res.case_id}`);
      router.push(`/cases/new/photos?case_id=${encodeURIComponent(res.case_id)}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save case. Please try again.");
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <StepIndicator step={1} />
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <FileText className="h-5 w-5" aria-hidden="true" />
            Tell us about the missing person
          </CardTitle>
          <CardDescription>
            Step 1 of 3 — basic details. We&apos;ll ask for photos next. Everything you share is
            stored securely and visible only to verified officers.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="person_name">Full name of the missing person</Label>
              <Input
                id="person_name"
                aria-invalid={Boolean(errors.person_name)}
                {...register("person_name")}
              />
              {errors.person_name && (
                <p className="text-xs text-destructive">{errors.person_name.message}</p>
              )}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="year_missing">Year missing</Label>
                <Controller
                  control={control}
                  name="year_missing"
                  render={({ field }) => (
                    <Select
                      value={String(field.value ?? "")}
                      onValueChange={(v) => field.onChange(Number(v))}
                    >
                      <SelectTrigger id="year_missing">
                        <SelectValue placeholder="Select year" />
                      </SelectTrigger>
                      <SelectContent className="max-h-60">
                        {YEARS.map((y) => (
                          <SelectItem key={y} value={String(y)}>
                            {y}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
                {errors.year_missing && (
                  <p className="text-xs text-destructive">{errors.year_missing.message}</p>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="age_at_disappearance">Age at disappearance</Label>
                <Input
                  id="age_at_disappearance"
                  type="number"
                  min={0}
                  max={100}
                  aria-invalid={Boolean(errors.age_at_disappearance)}
                  {...register("age_at_disappearance")}
                />
                {errors.age_at_disappearance && (
                  <p className="text-xs text-destructive">
                    {errors.age_at_disappearance.message}
                  </p>
                )}
              </div>
            </div>

            <div className="rounded-lg border bg-secondary/40 p-4">
              <div className="flex items-center gap-2 text-sm font-medium text-primary">
                <Info className="h-4 w-4" aria-hidden="true" />
                Predicted present-day age
                <span className="ml-auto rounded-full bg-accent px-3 py-1 text-base font-bold text-accent-foreground">
                  {predictedAge !== null ? predictedAge : "—"}
                </span>
              </div>
              <p className="mt-1.5 text-xs text-muted-foreground">
                Formula per FRS FR-2.2: age at disappearance + (current year − year missing) ={" "}
                {ageAtDis} + ({CURRENT_YEAR} − {yearMissing || "?"}). Why two photos? Two known
                ages let our <Acronym short="AI" /> learn the unique aging pattern between them,
                then extrapolate forward more accurately than from a single photograph.
              </p>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="last_seen_location">Last-seen city or area</Label>
              <Input
                id="last_seen_location"
                autoComplete="address-level2"
                placeholder="e.g. Ahmedabad railway station"
                aria-invalid={Boolean(errors.last_seen_location)}
                {...register("last_seen_location")}
              />
              {errors.last_seen_location && (
                <p className="text-xs text-destructive">
                  {errors.last_seen_location.message}
                </p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="identifying_marks">Identifying marks (optional)</Label>
              <Textarea
                id="identifying_marks"
                rows={3}
                placeholder="Scars, moles, birthmarks, tattoos…"
                {...register("identifying_marks")}
              />
            </div>

            {create.error && (
              <Alert variant="destructive">
                <AlertTitle>Could not save case</AlertTitle>
                <AlertDescription>{create.error.message}</AlertDescription>
              </Alert>
            )}

            <Button type="submit" size="lg" disabled={create.isPending}>
              {create.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
              Continue to photos <ArrowRight className="h-4 w-4" />
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

