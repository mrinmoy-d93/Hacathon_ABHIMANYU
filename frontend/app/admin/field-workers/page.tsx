"use client";

import { useState } from "react";
import { Loader2, MapPin, PencilLine, UserPlus } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
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
import { toast } from "@/components/ui/toast";
import { adminApi } from "@/lib/api";
import { useAdminFieldWorkers } from "@/lib/hooks/useAdmin";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { FieldWorkerRow } from "@/lib/types";

const ZONES = [
  "Ahmedabad North",
  "Ahmedabad South",
  "Surat Central",
  "Vadodara",
  "Rajkot",
  "Gandhinagar",
];

export default function FieldWorkersPage() {
  const { data, isLoading, error, refetch } = useAdminFieldWorkers();
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState<FieldWorkerRow | null>(null);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
          <div>
            <CardTitle className="text-primary">Field workers</CardTitle>
            <CardDescription>
              Assign zones, monitor verification counts and accuracy, manage leave.
            </CardDescription>
          </div>
          <Button onClick={() => setAddOpen(true)}>
            <UserPlus className="h-4 w-4" /> Add field worker
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex flex-col gap-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : error ? (
            <Alert variant="destructive">
              <AlertTitle>Could not load field workers</AlertTitle>
              <AlertDescription>{error.message}</AlertDescription>
            </Alert>
          ) : data && data.length > 0 ? (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Zone</TableHead>
                    <TableHead>Verifications</TableHead>
                    <TableHead className="min-w-[160px]">Accuracy</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((w) => (
                    <TableRow key={w.id}>
                      <TableCell className="font-medium">{w.name}</TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1 text-sm">
                          <MapPin className="h-3 w-3 text-muted-foreground" aria-hidden="true" />
                          {w.zone ?? <span className="text-muted-foreground">Unassigned</span>}
                        </span>
                      </TableCell>
                      <TableCell>{w.verification_count}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress
                            value={Math.round((w.accuracy_score ?? 0) * 100)}
                            className="w-24"
                            aria-label={`Accuracy ${Math.round((w.accuracy_score ?? 0) * 100)}%`}
                          />
                          <span className="text-xs font-medium">
                            {Math.round((w.accuracy_score ?? 0) * 100)}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" onClick={() => setEditing(w)}>
                          <PencilLine className="h-4 w-4" /> Edit
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="rounded-md border border-dashed p-10 text-center text-sm text-muted-foreground">
              No field workers yet. Add one to start dispatching alerts.
            </div>
          )}
        </CardContent>
      </Card>

      {addOpen && (
        <AddDialog open onClose={() => setAddOpen(false)} onAdded={() => refetch()} />
      )}
      {editing && (
        <EditDialog
          worker={editing}
          open
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            refetch();
          }}
        />
      )}
    </div>
  );
}

function AddDialog({
  open,
  onClose,
  onAdded,
}: {
  open: boolean;
  onClose: () => void;
  onAdded: () => void;
}) {
  const qc = useQueryClient();
  const [userId, setUserId] = useState("");
  const [zone, setZone] = useState(ZONES[0]);

  const mutation = useMutation({
    mutationFn: () => adminApi.assignFieldWorker({ user_id: userId.trim(), zone }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "fieldWorkers"] });
      toast.success("Field worker assigned.");
      onAdded();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add field worker</DialogTitle>
          <DialogDescription>
            Promote an existing user to field-worker role and assign them a zone.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="user-id">User ID</Label>
            <Input
              id="user-id"
              placeholder="e.g. 3f2a1b4c-…"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Search is not yet available — paste a user UUID from the audit log or database.
            </p>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="zone">Zone</Label>
            <Select value={zone} onValueChange={setZone}>
              <SelectTrigger id="zone">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ZONES.map((z) => (
                  <SelectItem key={z} value={z}>
                    {z}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!userId.trim() || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            Assign
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditDialog({
  worker,
  open,
  onClose,
  onSaved,
}: {
  worker: FieldWorkerRow;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const qc = useQueryClient();
  const [zone, setZone] = useState(worker.zone ?? ZONES[0]);
  const [onLeave, setOnLeave] = useState(false);

  const mutation = useMutation({
    mutationFn: () =>
      adminApi.updateFieldWorker(worker.id, {
        zone,
        leave_status: onLeave ? "on_leave" : "active",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "fieldWorkers"] });
      toast.success("Field worker updated.");
      onSaved();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit {worker.name}</DialogTitle>
          <DialogDescription>
            Reassign the zone or toggle leave. Open cases are automatically redistributed on
            leave.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor={`zone-${worker.id}`}>Zone</Label>
            <Select value={zone} onValueChange={setZone}>
              <SelectTrigger id={`zone-${worker.id}`}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ZONES.map((z) => (
                  <SelectItem key={z} value={z}>
                    {z}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between gap-2 rounded-md border p-3">
            <div>
              <p className="text-sm font-medium">On leave</p>
              <p className="text-xs text-muted-foreground">
                Open cases will be reassigned to other field workers in the same zone.
              </p>
            </div>
            <input
              type="checkbox"
              className="h-5 w-5 accent-primary"
              checked={onLeave}
              onChange={(e) => setOnLeave(e.target.checked)}
              aria-label="On leave toggle"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
