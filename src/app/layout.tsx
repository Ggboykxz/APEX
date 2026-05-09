import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "APEX — The Universal AI Coding Agent",
  description: "Every model. One terminal. APEX is the universal AI coding agent that runs in your terminal with 100+ models, 75+ tools, and 5 built-in agents. Built in Africa.",
  keywords: ["APEX", "AI coding agent", "terminal", "LLM", "Claude", "GPT", "Gemini", "coding assistant", "developer tools"],
  authors: [{ name: "Ggboykxz" }],
  icons: {
    icon: "/favicon.svg",
  },
  openGraph: {
    title: "APEX — The Universal AI Coding Agent",
    description: "Every model. One terminal. 100+ models, 75+ tools, 5 agents.",
    url: "https://apex-agent.dev",
    siteName: "APEX",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "APEX — The Universal AI Coding Agent",
    description: "Every model. One terminal. 100+ models, 75+ tools, 5 agents.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
