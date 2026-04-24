"use client";

import { useState } from "react";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Eye,
  Loader2,
  XCircle,
} from "lucide-react";

import { Acronym } from "@/components/Acronym";
import { AIBadge } from "@/components/AIBadge";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import {
  useAdminCases,
  useApproveCase,
  useRejectCase,
} from "@/lib/hooks/useAdmin";
import { useCase } from "@/lib/hooks/useCases";
import type { AdminCaseRow, CaseStatus } from "@/lib/types";

type Filter = "all" | CaseStatus;

const FILTERS: Array<{ value: Filter; label: string }> = [
  { value: "all", label: "All" },
  { value: "under_review", label: "Review Pending" },
  { value: "found", label: "Found" },
  { value: "closed", label: "Closed" },
];

export default function AdminCasesPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const [page, setPage] = useState(1);
  const [viewing, setViewing] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const status = filter === "all" ? undefined : filter;
  const casesQuery = useAdminCases({ status, page, page_size: 10 });
  const approve = useApproveCase();
  const reject = useRejectCase();

  const onApprove = async (caseId: string) => {
    try {
      await approve.mutateAsync(caseId);
      toast.success(`Approved ${caseId}. Field workers will be alerted.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not approve case.");
    }
  };

  const onReject = async () => {
    if (!rejecting) return;
    try {
      await reject.mutateAsync({ caseId: rejecting, reason: rejectReason.trim() || "Rejected" });
      toast.success(`Rejected ${rejecting}.`);
      setRejecting(null);
      setRejectReason("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not reject case.");
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-primary">Cases</CardTitle>
          <CardDescription>
            Approve or reject <Acronym short="AI" />-flagged cases. Approvals dispatch a field
            worker alert; rejections close the case with a reason.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <div className="flex min-w-[180px] flex-col gap-1.5">
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Status filter
              </label>
              <Select
                value={filter}
                onValueChange={(v) => {
                  setFilter(v as Filter);
                  setPage(1);
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FILTERS.map((f) => (
                    <SelectItem key={f.value} value={f.value}>
                      {f.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <AIBadge compact className="ml-auto" />
          </div>

          {casesQuery.isLoading ? (
            <TableSkeleton />
          ) : casesQuery.error ? (
            <Alert variant="destructive">
              <AlertTitle>Could not load cases</AlertTitle>
              <AlertDescription>{casesQuery.error.message}</AlertDescription>
            </Alert>
          ) : casesQuery.data && casesQuery.data.items.length > 0 ? (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Case ID</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Predicted age</TableHead>
                      <TableHead>Last-seen</TableHead>
                      <TableHead className="min-w-[140px]">Confidence</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {casesQuery.data.items.map((row) => (
                      <CaseRow
                        key={row.case_id}
                        row={row}
                        onView={() => setViewing(row.case_id)}
                        onApprove={() => onApprove(row.case_id)}
                        onReject={() => {
                          setRejecting(row.case_id);
                          setRejectReason("");
                        }}
                        approving={approve.isPending && approve.variables === row.case_id}
                      />
                    ))}
                  </TableBody>
                </Table>
              </div>

              <Pagination
                page={casesQuery.data.page}
                pageSize={casesQuery.data.page_size}
                total={casesQuery.data.total}
                onChange={setPage}
              />
            </>
          ) : (
            <EmptyState />
          )}
        </CardContent>
      </Card>

      {viewing && (
        <CaseDetailDialog caseId={viewing} open onOpenChange={() => setViewing(null)} />
      )}

      <Dialog
        open={Boolean(rejecting)}
        onOpenChange={(open) => {
          if (!open) {
            setRejecting(null);
            setRejectReason("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject case {rejecting}</DialogTitle>
            <DialogDescription>
              The family will be notified with the reason below. This action is logged in the
              audit chain.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            rows={4}
            placeholder="Reason for rejection (shared with the family)"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
          />
          <DialogFooter>
            <Button variant="ghost" onClick={() => setRejecting(null)} disabled={reject.isPending}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={onReject} disabled={reject.isPending}>
              {reject.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
              Reject
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CaseRow({
  row,
  onView,
  onApprove,
  onReject,
  approving,
}: {
  row: AdminCaseRow;
  onView: () => void;
  onApprove: () => void;
  onReject: () => void;
  approving: boolean;
}) {
  return (
    <TableRow>
      <TableCell className="font-mono text-xs">{row.case_id}</TableCell>
      <TableCell className="font-medium">{row.person_name}</TableCell>
      <TableCell>{row.predicted_current_age}</TableCell>
      <TableCell>{row.last_seen_location}</TableCell>
      <TableCell className="min-w-[160px]">
        {row.confidence_score !== null ? (
          <ConfidenceBar score={row.confidence_score} showLabel={false} />
        ) : (
          <span className="text-xs text-muted-foreground">pending</span>
        )}
      </TableCell>
      <TableCell>
        <StatusBadge status={row.status} />
      </TableCell>
      <TableCell>
        <div className="flex justify-end gap-1">
          <Button variant="ghost" size="icon" onClick={onView} aria-label="View details">
            <Eye className="h-4 w-4" />
          </Button>
          {row.status !== "found" && row.status !== "closed" && (
            <>
              <Button
                variant="ghost"
                size="icon"
                onClick={onApprove}
                aria-label="Approve"
                disabled={approving}
              >
                {approving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4 text-khojo-success" />
                )}
              </Button>
              <Button variant="ghost" size="icon" onClick={onReject} aria-label="Reject">
                <XCircle className="h-4 w-4 text-destructive" />
              </Button>
            </>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}

function StatusBadge({ status }: { status: CaseStatus }) {
  const map = {
    active: { variant: "secondary" as const, label: "Active" },
    under_review: { variant: "warning" as const, label: "Review" },
    found: { variant: "success" as const, label: "Found" },
    closed: { variant: "outline" as const, label: "Closed" },
  };
  const meta = map[status];
  return <Badge variant={meta.variant}>{meta.label}</Badge>;
}

function CaseDetailDialog({
  caseId,
  open,
  onOpenChange,
}: {
  caseId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data, isLoading, error } = useCase(caseId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-primary">Case {caseId}</DialogTitle>
          <DialogDescription>Full case record and <Acronym short="AI" /> matches.</DialogDescription>
        </DialogHeader>
        {isLoading ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : error ? (
          <Alert variant="destructive">
            <AlertTitle>Could not load case</AlertTitle>
            <AlertDescription>{error.message}</AlertDescription>
          </Alert>
        ) : data ? (
          <div className="flex flex-col gap-3 text-sm">
            <dl className="grid gap-3 sm:grid-cols-2">
              <Info label="Name" value={data.person_name} />
              <Info label="Status" value={<StatusBadge status={data.status} />} />
              <Info label="Age at disappearance" value={data.age_at_disappearance} />
              <Info label="Year missing" value={data.year_missing} />
              <Info label="Predicted current age" value={data.predicted_current_age} />
              <Info label="Last seen" value={data.last_seen_location} />
            </dl>
            {data.identifying_marks && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Identifying marks
                </p>
                <p className="mt-0.5 whitespace-pre-line">{data.identifying_marks}</p>
              </div>
            )}
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Matches ({data.matches.length})
              </p>
              {data.matches.length > 0 ? (
                <ul className="flex flex-col gap-2">
                  {data.matches.map((m) => (
                    <li key={m.id} className="rounded-md border p-2">
                      <ConfidenceBar score={m.confidence_score} tier={m.tier} />
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground">No matches yet.</p>
              )}
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function Info({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-0.5 font-medium">{value}</dd>
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
    <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
      <span>
        Page <strong>{page}</strong> of {lastPage} · {total} cases
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

function EmptyState() {
  return (
    <div className="rounded-md border border-dashed p-10 text-center">
      <p className="font-semibold">No cases match this filter</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Try a different status or wait for new registrations.
      </p>
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}
