"use client";

import { useEffect, useState } from "react";
import { Cpu, Loader2, Save, Sparkles } from "lucide-react";

import { Acronym } from "@/components/Acronym";
import { AIBadge } from "@/components/AIBadge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { toast } from "@/components/ui/toast";
import { useAdminSettings, useUpdateSettings } from "@/lib/hooks/useAdmin";
import type { Settings, SettingsUpdate } from "@/lib/types";

export default function AiSettingsPage() {
  const { data, isLoading, error } = useAdminSettings();
  const update = useUpdateSettings();

  // Local editable copy — syncs from server once and tracks user edits.
  const [draft, setDraft] = useState<Settings | null>(null);
  useEffect(() => {
    if (data) setDraft(data);
  }, [data]);

  if (isLoading || !draft) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-primary">
            <Acronym short="AI" /> Settings
          </CardTitle>
          <CardDescription>No-code threshold tuning per FRS §6.6 Tab 4.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load settings</AlertTitle>
        <AlertDescription>{error.message}</AlertDescription>
      </Alert>
    );
  }

  const confidencePct = Math.round(draft.confidence_threshold * 100);
  const autoAlertPct = Math.round(draft.auto_alert_threshold * 100);
  const invalid = confidencePct >= autoAlertPct;

  const save = async () => {
    if (!data) return;
    const payload: SettingsUpdate = {};
    if (draft.confidence_threshold !== data.confidence_threshold)
      payload.confidence_threshold = draft.confidence_threshold;
    if (draft.auto_alert_threshold !== data.auto_alert_threshold)
      payload.auto_alert_threshold = draft.auto_alert_threshold;
    if (draft.gpt4o_enabled !== data.gpt4o_enabled) payload.gpt4o_enabled = draft.gpt4o_enabled;
    if (draft.geo_clustering_enabled !== data.geo_clustering_enabled)
      payload.geo_clustering_enabled = draft.geo_clustering_enabled;

    if (Object.keys(payload).length === 0) {
      toast("No changes to save.");
      return;
    }

    try {
      await update.mutateAsync(payload);
      toast.success("Changes applied immediately — no redeploy needed.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save settings.");
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <Sparkles className="h-5 w-5 text-accent" aria-hidden="true" />
            <Acronym short="AI" /> Settings
          </CardTitle>
          <CardDescription>
            Tune review and alert thresholds without a code deploy. Saves apply immediately.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <SettingSlider
            id="confidence"
            label="Confidence review threshold"
            description="Matches at or above this confidence go to human review. Range 40–90%, default 60%."
            min={40}
            max={90}
            step={5}
            value={confidencePct}
            onChange={(pct) =>
              setDraft({ ...draft, confidence_threshold: pct / 100 })
            }
          />

          <SettingSlider
            id="auto-alert"
            label="Auto-alert threshold"
            description="Matches at or above this confidence trigger an immediate field-worker push. Range 60–99%, default 80%."
            min={60}
            max={99}
            step={1}
            value={autoAlertPct}
            onChange={(pct) =>
              setDraft({ ...draft, auto_alert_threshold: pct / 100 })
            }
          />

          {invalid && (
            <Alert variant="warning">
              <AlertTitle>Invalid range</AlertTitle>
              <AlertDescription>
                Confidence review threshold must be strictly lower than the auto-alert threshold.
              </AlertDescription>
            </Alert>
          )}

          <SettingToggle
            id="gpt4o"
            label="GPT-4o case summaries"
            description="Enable optional investigator case summaries and family notification copy."
            checked={draft.gpt4o_enabled}
            onCheckedChange={(v) => setDraft({ ...draft, gpt4o_enabled: v })}
          />

          <SettingToggle
            id="geo-clustering"
            label="Geo-clustering alerts"
            description="Raise an alert when three or more sightings cluster within 5 km."
            checked={draft.geo_clustering_enabled}
            onCheckedChange={(v) => setDraft({ ...draft, geo_clustering_enabled: v })}
          />

          <div className="rounded-md border bg-secondary/40 p-3 text-sm">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Cpu className="h-3 w-3" aria-hidden="true" /> Active AI model version
            </p>
            <p className="mt-1 font-mono text-base font-semibold text-primary">
              <Badge variant="accent">{draft.current_model_version}</Badge>
            </p>
          </div>

          <AIBadge />
        </CardContent>
        <CardFooter className="flex justify-end gap-2">
          <Button
            variant="ghost"
            onClick={() => data && setDraft(data)}
            disabled={update.isPending}
          >
            Revert
          </Button>
          <Button onClick={save} disabled={invalid || update.isPending}>
            {update.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Save className="h-4 w-4" aria-hidden="true" />
            )}
            Save changes
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}

function SettingSlider({
  id,
  label,
  description,
  min,
  max,
  step,
  value,
  onChange,
}: {
  id: string;
  label: string;
  description: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (pct: number) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-end justify-between gap-2">
        <div>
          <Label htmlFor={id}>{label}</Label>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
        <span className="rounded-md bg-accent/10 px-2 py-1 text-lg font-bold text-accent">
          {value}%
        </span>
      </div>
      <Slider
        id={id}
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={(v) => onChange(v[0] ?? min)}
      />
      <div className="flex justify-between text-[10px] uppercase tracking-wide text-muted-foreground">
        <span>{min}%</span>
        <span>{max}%</span>
      </div>
    </div>
  );
}

function SettingToggle({
  id,
  label,
  description,
  checked,
  onCheckedChange,
}: {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border p-3">
      <div>
        <Label htmlFor={id} className="block">
          {label}
        </Label>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <Switch id={id} checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  );
}
