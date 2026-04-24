"use client";

import { useEffect, useState } from "react";

import { getHealth } from "@/lib/api";

type Status = "checking" | "ok" | "error";

export function HealthCheck() {
  const [status, setStatus] = useState<Status>("checking");
  const [detail, setDetail] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((data) => {
        if (cancelled) return;
        setStatus("ok");
        setDetail(`${data.service ?? "backend"} v${data.version ?? "?"} · ${data.environment ?? ""}`);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setStatus("error");
        setDetail(err instanceof Error ? err.message : "Unknown error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const badge = {
    checking: { text: "Checking…", className: "bg-slate-700 text-slate-200" },
    ok: { text: "Online", className: "bg-khojo-success text-white" },
    error: { text: "Offline", className: "bg-khojo-danger text-white" },
  }[status];

  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${badge.className}`}>
        {badge.text}
      </span>
      <span className="text-sm text-slate-400">{detail || "Pinging /health…"}</span>
    </div>
  );
}
