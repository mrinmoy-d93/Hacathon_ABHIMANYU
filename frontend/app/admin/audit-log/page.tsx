"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Download, Loader2, ShieldCheck } from "lucide-react";

import { Acronym } from "@/components/Acronym";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "@/components/ui/toast";
import { useAuditLog, useExportAuditLog } from "@/lib/hooks/useAdmin";

export default function AuditLogPage() {
  const [from, setFrom] = useState<string>("");
  const [to, setTo] = useState<string>("");
  const [page, setPage] = useState(1);

  const params = {
    from: from || undefined,
    to: to || undefined,
    page,
    page_size: 25,
  } as const;

  const query = useAuditLog(params);
  const exportMut = useExportAuditLog();

  const onExport = async () => {
    try {
      await exportMut.mutateAsync({ from: from || undefined, to: to || undefined });
      toast.success("Audit log exported.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Export failed.");
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <ShieldCheck className="h-5 w-5 text-accent" aria-hidden="true" />
            Audit log
          </CardTitle>
          <CardDescription>
            Every <Acronym short="AI" /> decision is cryptographically signed.{" "}
            <Acronym short="PII" /> is redacted per FRS §10.2.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="from">From</Label>
              <Input
                id="from"
                type="date"
                value={from}
                onChange={(e) => {
                  setFrom(e.target.value);
                  setPage(1);
                }}
                className="w-40"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="to">To</Label>
              <Input
                id="to"
                type="date"
                value={to}
                onChange={(e) => {
                  setTo(e.target.value);
                  setPage(1);
                }}
                className="w-40"
              />
            </div>
            <Button className="ml-auto" variant="outline" onClick={onExport} disabled={exportMut.isPending}>
              {exportMut.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Download className="h-4 w-4" aria-hidden="true" />
              )}
              Export <Acronym short="CSV" />
            </Button>
          </div>

          {query.isLoading ? (
            <div className="flex flex-col gap-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : query.error ? (
            <Alert variant="destructive">
              <AlertTitle>Could not load audit log</AlertTitle>
              <AlertDescription>{query.error.message}</AlertDescription>
            </Alert>
          ) : query.data && query.data.items.length > 0 ? (
            <>
              <div className="overflow-x-auto rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Timestamp</TableHead>
                      <TableHead>Actor</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Model</TableHead>
                      <TableHead>Confidence</TableHead>
                      <TableHead>Signature (first 8)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {query.data.items.map((entry) => (
                      <TableRow key={entry.id}>
                        <TableCell className="whitespace-nowrap text-xs">
                          {new Date(entry.timestamp).toLocaleString()}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {entry.actor_id ? entry.actor_id.slice(0, 8) : "system"}
                        </TableCell>
                        <TableCell className="text-sm font-medium">
                          {entry.action}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {entry.model_version ?? "—"}
                        </TableCell>
                        <TableCell className="text-xs">
                          {entry.confidence_score !== null
                            ? `${Math.round(entry.confidence_score * 100)}%`
                            : "—"}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {entry.output_hash ? entry.output_hash.slice(0, 8) : "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <Pagination
                page={query.data.page}
                pageSize={query.data.page_size}
                total={query.data.total}
                onChange={setPage}
              />
            </>
          ) : (
            <div className="rounded-md border border-dashed p-10 text-center text-sm text-muted-foreground">
              No audit entries in this range.
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            Every AI decision is cryptographically signed. <Acronym short="PII" /> is redacted per
            FRS <Acronym short="FRS" />-AL-2, AL-3.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function Pagination({
  page,
  pageSize,
  total,
  onChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}) {
  const lastPage = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex items-center justify-between text-sm text-muted-foreground">
      <span>
        Page <strong>{page}</strong> of {lastPage} · {total} entries
      </span>
      <div className="flex gap-1">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
        >
          <ChevronLeft className="h-4 w-4" /> Prev
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange(page + 1)}
          disabled={page >= lastPage}
        >
          Next <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
