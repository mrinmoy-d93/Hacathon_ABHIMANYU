import { cn } from "@/lib/utils";
import type { MatchTier } from "@/lib/types";

/**
 * Tier thresholds per FRS FR-3.7 / FR-4.2:
 *   High ≥ 80% (green), Medium 60–80% (amber), Low < 60% (red).
 */
export function tierForScore(score: number): MatchTier {
  if (score >= 0.8) return "high";
  if (score >= 0.6) return "medium";
  return "low";
}

const TIER_META: Record<
  MatchTier,
  { label: string; bar: string; badge: string; text: string }
> = {
  high: {
    label: "High confidence",
    bar: "bg-khojo-success",
    badge: "bg-khojo-success text-white",
    text: "text-khojo-success",
  },
  medium: {
    label: "Medium confidence",
    bar: "bg-khojo-warning",
    badge: "bg-khojo-warning text-white",
    text: "text-khojo-warning",
  },
  low: {
    label: "Low confidence",
    bar: "bg-khojo-danger",
    badge: "bg-khojo-danger text-white",
    text: "text-khojo-danger",
  },
};

interface ConfidenceBarProps {
  /** Score in [0, 1]. */
  score: number;
  /** Optional tier override (used when the backend already decided the tier). */
  tier?: MatchTier;
  className?: string;
  showLabel?: boolean;
}

export function ConfidenceBar({ score, tier, className, showLabel = true }: ConfidenceBarProps) {
  const safe = Math.max(0, Math.min(1, Number.isFinite(score) ? score : 0));
  const resolved = tier ?? tierForScore(safe);
  const pct = Math.round(safe * 100);
  const meta = TIER_META[resolved];

  return (
    <div
      className={cn("flex flex-col gap-2", className)}
      role="img"
      aria-label={`${meta.label}: ${pct} percent`}
    >
      <div className="flex items-center justify-between text-sm">
        <span className={cn("font-semibold", meta.text)}>{pct}%</span>
        {showLabel && (
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-xs font-semibold uppercase tracking-wide",
              meta.badge
            )}
          >
            {resolved}
          </span>
        )}
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className={cn("h-full rounded-full transition-[width]", meta.bar)}
          style={{ width: `${pct}%` }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}
