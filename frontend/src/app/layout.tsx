import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import { JsonLd, webApplicationLd } from "@/components/json-ld";

import { Providers } from "@/components/providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "AI Resume Matcher — Check your resume against any job description",
    template: "%s · AI Resume Matcher",
  },
  description:
    "Upload your resume, paste a job description, and get a hybrid match score with missing keywords and AI-powered suggestions to close the gap.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <JsonLd data={webApplicationLd()} />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
