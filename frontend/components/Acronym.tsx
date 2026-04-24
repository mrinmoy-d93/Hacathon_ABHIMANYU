"use client";
import {
  createContext,
  useContext,
  useRef,
  type ReactNode,
} from "react";

import { ACRONYMS } from "@/lib/acronyms";

/**
 * Per-screen acronym expansion per FRS FR-4.5 / AC-7.
 *
 * Wrap each page in <AcronymProvider> and use <Acronym short="AI" /> wherever
 * an acronym appears. The first render of each `short` on the page emits the
 * full form "Artificial Intelligence (AI)"; subsequent uses render "AI".
 */
interface AcronymTracker {
  seen: Set<string>;
}

const AcronymContext = createContext<AcronymTracker | null>(null);

export function AcronymProvider({ children }: { children: ReactNode }) {
  // useRef survives re-renders but resets per page render tree. That's the
  // behaviour we want: reset expansions each time a page is mounted.
  const trackerRef = useRef<AcronymTracker>({ seen: new Set() });
  return (
    <AcronymContext.Provider value={trackerRef.current}>{children}</AcronymContext.Provider>
  );
}

interface AcronymProps {
  short: keyof typeof ACRONYMS | string;
  /** Force the long form regardless of prior occurrences. */
  forceLong?: boolean;
}

export function Acronym({ short, forceLong = false }: AcronymProps) {
  const tracker = useContext(AcronymContext);
  const long = ACRONYMS[short];
  // If not in registry, just render the raw token.
  if (!long) return <>{short}</>;

  const seen = tracker?.seen.has(short) ?? false;
  if (tracker) tracker.seen.add(short);

  if (!seen || forceLong) {
    return (
      <abbr title={long} className="no-underline">
        {long} ({short})
      </abbr>
    );
  }
  return (
    <abbr title={long} className="no-underline">
      {short}
    </abbr>
  );
}
