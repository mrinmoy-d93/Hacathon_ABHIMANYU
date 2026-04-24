import { User } from "lucide-react";
import { cn } from "@/lib/utils";

export interface PhotoComparePane {
  src: string | null;
  label: string;
  caption?: string;
}

interface PhotoCompareProps {
  left: PhotoComparePane;
  right: PhotoComparePane;
  className?: string;
}

/**
 * Side-by-side photo display used on the Result screen (FRS FR-4.1) and the
 * Field-Worker Verify screen (FRS §6.5). Falls back to an icon placeholder when
 * a photo URL is missing so layout never collapses.
 */
export function PhotoCompare({ left, right, className }: PhotoCompareProps) {
  return (
    <div className={cn("grid grid-cols-1 gap-4 sm:grid-cols-2", className)}>
      <Pane {...left} />
      <Pane {...right} />
    </div>
  );
}

function Pane({ src, label, caption }: PhotoComparePane) {
  return (
    <figure className="flex flex-col gap-2">
      <div className="relative aspect-square w-full overflow-hidden rounded-lg border bg-muted">
        {src ? (
          // Use raw <img> (not next/image) so remote Supabase URLs work without
          // whitelisting every domain in next.config.js.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={src}
            alt={label}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-muted-foreground">
            <User className="h-16 w-16" aria-hidden="true" />
            <span className="sr-only">No photo available</span>
          </div>
        )}
      </div>
      <figcaption className="text-center">
        <p className="text-sm font-medium">{label}</p>
        {caption && <p className="text-xs text-muted-foreground">{caption}</p>}
      </figcaption>
    </figure>
  );
}
