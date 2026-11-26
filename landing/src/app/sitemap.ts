import type { MetadataRoute } from "next";
import { SITE_CONFIG } from "@/config/site";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: `${SITE_CONFIG.siteUrl}/`,
      lastModified: new Date("2026-11-27T00:00:00.000Z"),
      changeFrequency: "weekly",
      priority: 1,
    },
  ];
}
