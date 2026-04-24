"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useRef, useState } from "react";
import { ArrowRight, Camera, ImagePlus, Loader2, Trash2, UploadCloud } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { Acronym, AcronymProvider } from "@/components/Acronym";
import { AuthHydrationGuard } from "@/components/AuthHydrationGuard";
import { StepIndicator } from "@/components/StepIndicator";
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
import { toast } from "@/components/ui/toast";
import { useProcessCase, useUploadPhoto } from "@/lib/hooks/useCases";
import { cn } from "@/lib/utils";

interface LocalPhoto {
  id: string;
  file: File;
  preview: string;
  age: number;
  uploaded: boolean;
}

export default function PhotosPage() {
  return (
    <AppShell>
      <AcronymProvider>
        <AuthHydrationGuard requiredRole={["family", "field_worker", "admin"]}>
          <Suspense
            fallback={
              <div className="flex justify-center py-12 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
              </div>
            }
          >
            <PhotosInner />
          </Suspense>
        </AuthHydrationGuard>
      </AcronymProvider>
    </AppShell>
  );
}

function PhotosInner() {
  const router = useRouter();
  const params = useSearchParams();
  const caseId = params.get("case_id") ?? "";

  const [photos, setPhotos] = useState<LocalPhoto[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);

  const upload = useUploadPhoto(caseId);
  const process = useProcessCase(caseId);

  if (!caseId) {
    return (
      <div className="mx-auto max-w-xl">
        <Alert variant="destructive">
          <AlertTitle>Missing case reference</AlertTitle>
          <AlertDescription>Please start a new case from the beginning.</AlertDescription>
        </Alert>
        <Button className="mt-4" onClick={() => router.push("/cases/new/details")}>
          Start over
        </Button>
      </div>
    );
  }

  const addFiles = (files: FileList | File[]) => {
    const accepted: LocalPhoto[] = [];
    Array.from(files).forEach((file) => {
      if (!file.type.startsWith("image/")) {
        toast.error(`${file.name}: not an image file.`);
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        toast.error(`${file.name}: exceeds 10 MB limit.`);
        return;
      }
      accepted.push({
        id: `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2, 8)}`,
        file,
        preview: URL.createObjectURL(file),
        age: 0,
        uploaded: false,
      });
    });
    setPhotos((prev) => [...prev, ...accepted]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files) addFiles(e.dataTransfer.files);
  };

  const removePhoto = (id: string) => {
    setPhotos((prev) => {
      const removed = prev.find((p) => p.id === id);
      if (removed) URL.revokeObjectURL(removed.preview);
      return prev.filter((p) => p.id !== id);
    });
  };

  const updateAge = (id: string, age: number) => {
    setPhotos((prev) => prev.map((p) => (p.id === id ? { ...p, age } : p)));
  };

  const ready =
    photos.length >= 2 && photos.every((p) => Number.isFinite(p.age) && p.age > 0 && p.age <= 100);

  const onContinue = async () => {
    if (!ready) {
      toast.error("Please upload at least 2 photos and tag each with an age.");
      return;
    }
    setBusy(true);
    try {
      for (const photo of photos) {
        if (photo.uploaded) continue;
        await upload.mutateAsync({ file: photo.file, age_at_photo: photo.age });
        setPhotos((prev) =>
          prev.map((p) => (p.id === photo.id ? { ...p, uploaded: true } : p))
        );
      }
      await process.mutateAsync();
      toast.success("Processing started — the AI pipeline is running.");
      router.push(`/cases/new/processing?case_id=${encodeURIComponent(caseId)}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed. Please retry.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <StepIndicator step={2} />
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <ImagePlus className="h-5 w-5" aria-hidden="true" />
            Upload photos
          </CardTitle>
          <CardDescription>
            Step 2 of 3 — minimum <strong>2 photos</strong> per FRS FR-2.3. More photos = better{" "}
            <Acronym short="AI" /> accuracy. Tag the age for each photo.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div
            role="button"
            tabIndex={0}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                fileInputRef.current?.click();
              }
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
              dragOver
                ? "border-accent bg-accent/5"
                : "border-border bg-secondary/30 hover:bg-secondary/50"
            )}
            aria-label="Drop photos here or click to upload"
          >
            <UploadCloud className="h-10 w-10 text-accent" aria-hidden="true" />
            <p className="text-sm font-medium text-primary">
              Drag photos here, or tap to choose files
            </p>
            <p className="text-xs text-muted-foreground">JPG or PNG, up to 10 MB each.</p>
            <div className="mt-2 flex flex-wrap justify-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={(e) => {
                  e.stopPropagation();
                  cameraInputRef.current?.click();
                }}
              >
                <Camera className="h-4 w-4" />
                Take photo
              </Button>
            </div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files) addFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <input
            ref={cameraInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => {
              if (e.target.files) addFiles(e.target.files);
              e.target.value = "";
            }}
          />

          {photos.length > 0 ? (
            <ul className="grid gap-3 sm:grid-cols-2">
              {photos.map((p) => (
                <li key={p.id} className="flex gap-3 rounded-lg border bg-card p-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={p.preview}
                    alt={p.file.name}
                    className="h-24 w-24 shrink-0 rounded-md object-cover"
                  />
                  <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                    <p className="truncate text-sm font-medium">{p.file.name}</p>
                    <Label htmlFor={`age-${p.id}`} className="text-xs text-muted-foreground">
                      Age at this photo
                    </Label>
                    <Input
                      id={`age-${p.id}`}
                      type="number"
                      min={1}
                      max={100}
                      value={p.age || ""}
                      onChange={(e) => updateAge(p.id, Number(e.target.value))}
                      placeholder="e.g. 7"
                      className="h-9"
                    />
                    {p.uploaded && (
                      <span className="text-xs font-medium text-khojo-success">
                        ✓ Uploaded
                      </span>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removePhoto(p.id)}
                    aria-label={`Remove ${p.file.name}`}
                    disabled={busy}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
              No photos yet. Please add at least 2 to continue.
            </p>
          )}

          {!ready && photos.length > 0 && (
            <Alert variant="info">
              <AlertTitle>Almost there</AlertTitle>
              <AlertDescription>
                {photos.length < 2
                  ? `Please add ${2 - photos.length} more photo${photos.length === 1 ? "" : "s"}.`
                  : "Please enter an age (1–100) for every photo."}
              </AlertDescription>
            </Alert>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-muted-foreground">
              Case reference: <code className="font-mono">{caseId}</code>
            </p>
            <Button
              type="button"
              size="lg"
              onClick={onContinue}
              disabled={!ready || busy}
              className="ml-auto"
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
              {busy ? "Uploading…" : "Continue"}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
