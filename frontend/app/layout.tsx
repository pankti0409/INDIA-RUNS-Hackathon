import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Redrob Ranker — Intelligent Candidate Discovery",
  description:
    "AI-powered candidate ranking system for the Redrob ML Engineer role. Top 100 candidates ranked by semantic fit, behavioral signals, and technical validation.",
  keywords: "candidate ranking, AI, ML engineer, NLP, retrieval, Redrob hackathon",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body style={{ fontFamily: "var(--font-inter), sans-serif" }} className={inter.variable}>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
