/**
 * 4-step horizontal progress indicator shown across the case registration
 * flow (FRS §6.2–§6.4): Details → Photos → Processing → Result.
 */
export function StepIndicator({ step }: { step: 1 | 2 | 3 | 4 }) {
  const labels = ["Details", "Photos", "Processing", "Result"];
  return (
    <ol
      className="mb-6 flex items-center gap-1 text-xs sm:text-sm"
      aria-label="Case registration progress"
    >
      {labels.map((label, i) => {
        const idx = i + 1;
        const active = idx === step;
        const done = idx < step;
        return (
          <li key={label} className="flex flex-1 items-center gap-1">
            <span
              className={
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold " +
                (active
                  ? "border-primary bg-primary text-primary-foreground"
                  : done
                    ? "border-khojo-success bg-khojo-success text-white"
                    : "border-muted-foreground/30 bg-background text-muted-foreground")
              }
              aria-current={active ? "step" : undefined}
            >
              {idx}
            </span>
            <span
              className={
                "truncate " +
                (active ? "font-semibold text-primary" : "text-muted-foreground")
              }
            >
              {label}
            </span>
            {idx < labels.length && <span className="h-px flex-1 bg-border" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
  );
}
