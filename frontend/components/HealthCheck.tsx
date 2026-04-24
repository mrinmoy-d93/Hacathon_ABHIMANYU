"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
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
        setStatus(data.status === "ok" ? "ok" : "error");
        const configured = Object.entries(data.providers)
          .filter(([, enabled]) => enabled)
          .map(([name]) => name);
        setDetail(
          `KHOJO API v${data.version} · db=${data.db ? "up" : "down"} · providers=${
            configured.length ? configured.join(",") : "none"
          }`
        );
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

  const label = {
    checking: "Checking…",
    ok: "Online",
    error: "Offline",
  }[status];

  const variant = status === "ok" ? "success" : status === "error" ? "destructive" : "secondary";

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Badge variant={variant}>{label}</Badge>
      <span className="text-sm text-muted-foreground">{detail || "Pinging /health…"}</span>
    </div>
  );
}
