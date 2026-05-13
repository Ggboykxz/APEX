import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { APP_NAME, APP_DESCRIPTION, APP_VERSION_TAG, APP_MODEL_COUNT, APP_AGENT_COUNT_TOTAL } from "@/lib/version";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const META_DESC = `Every model. One terminal. ${APP_NAME} is the universal AI coding agent that runs in your terminal with ${APP_MODEL_COUNT} models, 75+ tools, and ${APP_AGENT_COUNT_TOTAL} built-in agents. Built in Africa.`;
const META_SHORT = `Every model. One terminal. ${APP_MODEL_COUNT} models, 75+ tools, ${APP_AGENT_COUNT_TOTAL} agents.`;

export const metadata: Metadata = {
  title: `${APP_NAME} — The Universal AI Coding Agent`,
  description: META_DESC,
  keywords: ["APEX", "AI coding agent", "terminal", "LLM", "Claude", "GPT", "Gemini", "coding assistant", "developer tools"],
  authors: [{ name: "Ggboykxz" }],
  icons: {
    icon: "/favicon.svg",
  },
  openGraph: {
    title: `${APP_NAME} — The Universal AI Coding Agent`,
    description: META_SHORT,
    url: "https://apex-ai.dev",
    siteName: APP_NAME,
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: `${APP_NAME} — The Universal AI Coding Agent`,
    description: META_SHORT,
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
