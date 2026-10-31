import type { Metadata, Viewport } from "next";
import { Hanken_Grotesk, IBM_Plex_Mono } from "next/font/google";

import "./globals.css";

const sans = Hanken_Grotesk({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

const description =
  "BreachLens tests AI applications with controlled adversarial prompts and records two separate results for every attempt: how the model behaved, and whether the guardrails around it held.";

// Public origin used to build absolute canonical and sharing URLs. These tags are
// emitted only when NEXT_PUBLIC_SITE_URL is set at build time; without it no localhost
// URL is baked into the page.
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL?.trim() || undefined;

const socialImages = siteUrl
  ? [
      {
        url: "/brand/breachlens-og.png",
        width: 1200,
        height: 630,
        alt: "BreachLens. See where the model breaks. And where the system holds.",
      },
    ]
  : undefined;

export const metadata: Metadata = {
  ...(siteUrl ? { metadataBase: new URL(siteUrl), alternates: { canonical: "/" } } : {}),
  title: "BreachLens — See where the model breaks, and where the system holds",
  description,
  applicationName: "BreachLens",
  openGraph: {
    title: "BreachLens",
    description,
    siteName: "BreachLens",
    type: "website",
    ...(siteUrl ? { url: "/" } : {}),
    ...(socialImages ? { images: socialImages } : {}),
  },
  twitter: {
    card: socialImages ? "summary_large_image" : "summary",
    title: "BreachLens",
    description,
    ...(socialImages ? { images: socialImages } : {}),
  },
};

export const viewport: Viewport = {
  themeColor: "#0A0A0B",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
