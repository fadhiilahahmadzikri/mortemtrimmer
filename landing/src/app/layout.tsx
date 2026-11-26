import type { Metadata } from "next";
import { DM_Sans, IBM_Plex_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
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
  metadataBase: new URL(SITE_CONFIG.siteUrl),
  title: SITE_CONFIG.seoTitle,
  description: SITE_CONFIG.seoDescription,
  keywords: [...SITE_CONFIG.keywords],
  authors: [{ name: SITE_CONFIG.authorName, url: SITE_CONFIG.authorUrl }],
  creator: SITE_CONFIG.authorName,
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: SITE_CONFIG.seoTitle,
    description: SITE_CONFIG.seoDescription,
    url: SITE_CONFIG.siteUrl,
    siteName: SITE_CONFIG.name,
    type: "website",
    images: [
      {
        url: SITE_CONFIG.ogImagePath,
        width: SITE_CONFIG.ogImageWidth,
        height: SITE_CONFIG.ogImageHeight,
        alt: SITE_CONFIG.ogImageAlt,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_CONFIG.seoTitle,
    description: SITE_CONFIG.seoDescription,
    images: [SITE_CONFIG.ogImagePath],
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${dmSans.variable} ${ibmPlexMono.variable} h-full`}
    >
      <body className="relative min-h-svh w-full flex flex-col">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
