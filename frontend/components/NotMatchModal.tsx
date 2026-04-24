"use client";
import { useRef, useState } from "react";
import { Camera, Loader2, UploadCloud, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "@/components/ui/toast";
import { useNotMatch } from "@/lib/hooks/useMatches";
import type { NotMatchResponse } from "@/lib/types";

interface NotMatchModalProps {
  matchId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (result: NotMatchResponse) => void;
}

/**
 * Modal per FRS FR-5.4 — mandatory upload of the actual person's photograph
 * before a "Not a Match" can be submitted. Submit stays disabled until a
 * photo is selected.
 */
export function NotMatchModal({ matchId, open, onOpenChange, onSuccess }: NotMatchModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const cameraRef = useRef<HTMLInputElement | null>(null);
  const notMatch = useNotMatch();

  const reset = () => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
  };

  const selectFile = (f: File | null) => {
    if (preview) URL.revokeObjectURL(preview);
    if (!f) {
      setFile(null);
      setPreview(null);
      return;
    }
    if (!f.type.startsWith("image/")) {
      toast.error("Please select an image file.");
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      toast.error("Photo exceeds the 10 MB limit.");
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const onSubmit = async () => {
    if (!file) return;
    try {
      const res = await notMatch.mutateAsync({ matchId, realPhoto: file });
      onSuccess(res);
      reset();
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not submit feedback.");
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-primary">
            <XCircle className="h-5 w-5 text-khojo-warning" aria-hidden="true" />
            Not a Match — upload real photo
          </DialogTitle>
          <DialogDescription>
            Upload a photo of the actual person you met. This helps the Artificial Intelligence
            learn from the mismatch — every &ldquo;Not a Match&rdquo; makes KHOJO smarter.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center gap-3">
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={preview}
              alt="Uploaded"
              className="h-48 w-48 rounded-md border object-cover"
            />
          ) : (
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="flex h-48 w-48 flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed text-muted-foreground transition-colors hover:border-accent hover:bg-accent/5"
            >
              <UploadCloud className="h-8 w-8" aria-hidden="true" />
              <span className="text-sm">Tap to choose a photo</span>
            </button>
          )}
          <div className="flex flex-wrap justify-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => fileRef.current?.click()}
            >
              <UploadCloud className="h-4 w-4" /> Choose file
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => cameraRef.current?.click()}
            >
              <Camera className="h-4 w-4" /> Take photo
            </Button>
            {file && (
              <Button type="button" variant="ghost" size="sm" onClick={reset}>
                Clear
              </Button>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => selectFile(e.target.files?.[0] ?? null)}
          />
          <input
            ref={cameraRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => selectFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={notMatch.isPending}>
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={!file || notMatch.isPending}>
            {notMatch.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            Submit feedback
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
