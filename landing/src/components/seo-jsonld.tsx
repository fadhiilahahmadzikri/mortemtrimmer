import { SITE_CONFIG } from "@/config/site";

export function SeoJsonLd() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "SoftwareApplication",
        name: SITE_CONFIG.name,
        operatingSystem: "Windows 10, Windows 11 (x64)",
        applicationCategory: "MultimediaApplication",
        softwareVersion: SITE_CONFIG.version,
        description: SITE_CONFIG.seoDescription,
        url: SITE_CONFIG.siteUrl,
        downloadUrl: SITE_CONFIG.downloadUrl,
        license: SITE_CONFIG.licenseUrl,
        image: `${SITE_CONFIG.siteUrl}${SITE_CONFIG.logoPath}`,
        author: {
          "@type": "Person",
          name: SITE_CONFIG.authorName,
          url: SITE_CONFIG.authorUrl,
        },
        offers: {
          "@type": "Offer",
          price: "0",
          priceCurrency: "USD",
        },
      },
      {
        "@type": "FAQPage",
        mainEntity: SITE_CONFIG.faq.map((item) => ({
          "@type": "Question",
          name: item.question,
          acceptedAnswer: {
            "@type": "Answer",
            text: item.answer,
          },
        })),
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(structuredData).replace(/</g, "\\u003c"),
      }}
    />
  );
}
