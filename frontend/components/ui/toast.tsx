"use client";
import { Toaster as SonnerToaster, toast } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      position="top-right"
      richColors
      closeButton
      toastOptions={{
        className:
          "bg-background text-foreground border border-border shadow-lg rounded-lg",
      }}
    />
  );
}

export { toast };
