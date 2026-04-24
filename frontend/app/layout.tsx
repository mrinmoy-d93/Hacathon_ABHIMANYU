import type { Metadata } from "next";

import { QueryProvider } from "@/components/QueryProvider";

import "./globals.css";

export const metadata: Metadata = {
  title: "KHOJO — AI Missing Person Finder",
  description:
    "An Artificial Intelligence (AI) powered solution to locate missing persons through facial aging prediction and age-invariant face recognition.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
