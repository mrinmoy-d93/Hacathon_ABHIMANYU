import { Sparkles, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Persistent disclaimer per FRS FR-4.4:
 * "This is an estimate produced by Artificial Intelligence (AI). Please have
 * the result verified by a certified officer before acting upon it."
 *
 * Shown on every screen that displays AI output.
 */
export function AIBadge({ className, compact = false }: { className?: string; compact?: boolean }) {
  if (compact) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-full border border-khojo-warning/40 bg-khojo-warning/10 px-2.5 py-1 text-xs font-medium text-khojo-warning",
          className
        )}
        role="note"
      >
        <Sparkles className="h-3 w-3" aria-hidden="true" />
        Artificial Intelligence (AI) estimate — verify with officer
      </span>
    );
  }
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border border-khojo-warning/40 bg-khojo-warning/5 p-3 text-sm text-khojo-warning",
        className
      )}
      role="note"
      aria-label="AI estimate disclaimer"
    >
      <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
      <p>
        This is an estimate produced by <strong>Artificial Intelligence (AI)</strong>. Please have
        the result verified by a certified officer before acting upon it.
      </p>
    </div>
  );
}
