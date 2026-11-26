import type { Metadata } from "next";
import { DM_Sans, IBM_Plex_Mono } from "next/font/google";
import { SITE_CONFIG } from "@/config/site";
import "./globals.css";

const dmSans = DM_Sans({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-code",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: `${SITE_CONFIG.name} — Offline AI Silence Remover`,
  description: SITE_CONFIG.tagline,
  openGraph: {
    title: SITE_CONFIG.name,
    description: SITE_CONFIG.tagline,
    type: "website",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${dmSans.variable} ${ibmPlexMono.variable} h-full`}
    >
      <body className="relative min-h-svh w-full flex flex-col">
        {children}
      </body>
    </html>
  );
}
