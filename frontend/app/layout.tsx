import type { Metadata, Viewport } from "next";

import { QueryProvider } from "@/components/QueryProvider";
import { Toaster } from "@/components/ui/toast";

import "./globals.css";

export const metadata: Metadata = {
  title: "KHOJO — Find the Missing",
  description:
    "Every year tens of thousands of people — especially children — go missing in India. KHOJO uses Artificial Intelligence (AI) facial-aging to predict how a missing person looks today and match them against a growing database of sightings.",
  applicationName: "KHOJO",
  authors: [{ name: "Team KHOJO" }],
  keywords: ["KHOJO", "missing person", "facial aging", "AI", "India", "Amnex"],
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0d2b4e",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background text-foreground antialiased">
        <QueryProvider>
          {children}
          <Toaster />
        </QueryProvider>
      </body>
    </html>
  );
}
