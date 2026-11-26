import type { ComponentType } from "react";
import { Cpu, MousePointerClick, ShieldCheck } from "lucide-react";
import { FaqSection } from "@/components/faq-section";
import { HeroCard } from "@/components/hero-card";
import {
  CornerAnchorSquares,
  DashedHorizontalRule,
  DotBackdrop,
  RailSection,
} from "@/components/rail-frame";
import { SeoJsonLd } from "@/components/seo-jsonld";
import { SetupSection } from "@/components/setup-section";
import { SiteHeader } from "@/components/site-header";
import { type FeaturePillar, SITE_CONFIG } from "@/config/site";

const PILLAR_ICONS: Record<
  FeaturePillar["id"],
  ComponentType<{ className?: string }>
> = {
  offline: Cpu,
  explorer: MousePointerClick,
  verified: ShieldCheck,
};

export default function Home() {
  return (
    <div className="relative flex min-h-svh w-full flex-col overflow-x-clip bg-background">
      <SeoJsonLd />
      <DotBackdrop />
      <SiteHeader />

      <main className="relative z-10 flex flex-1 flex-col">
        <HeroCard />

        <RailSection id="capabilities" className="pt-4 pb-6 md:pt-6 md:pb-8">
          <div className="relative mx-auto grid grid-cols-1 border-y border-border bg-background md:grid-cols-3">
            <CornerAnchorSquares />

            {SITE_CONFIG.pillars.map((pillar, index) => {
              const Icon = PILLAR_ICONS[pillar.id];
              return (
                <article
                  key={pillar.id}
                  className={
                    index > 0
                      ? "flex flex-col items-start gap-2 border-t border-border bg-background p-6 md:border-t-0 md:border-l md:p-7"
                      : "flex flex-col items-start gap-2 bg-background p-6 md:p-7"
                  }
                >
                  <Icon className="size-6 stroke-[1.6] text-foreground" />
                  <h2 className="pt-1 text-[16px] font-medium tracking-[-0.01em] text-foreground">
                    {pillar.title}
                  </h2>
                  <p className="text-[14px] leading-[1.45] text-muted-foreground">
                    {pillar.description}
                  </p>
                </article>
              );
            })}
          </div>
        </RailSection>

        <FaqSection />
        <SetupSection />
      </main>

      <footer className="relative z-10 w-full overflow-x-clip">
        <DashedHorizontalRule />
        <RailSection className="flex flex-col items-start justify-between gap-2 px-6 py-4 font-mono text-xs text-muted-foreground sm:flex-row sm:items-center">
          <p>
            {SITE_CONFIG.name} · {SITE_CONFIG.licenseLabel} · by{" "}
            <a
              href={SITE_CONFIG.authorUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-foreground underline decoration-border underline-offset-4 hover:decoration-foreground"
            >
              {SITE_CONFIG.authorName}
            </a>
          </p>
          <div className="flex items-center gap-4">
            <a
              href={SITE_CONFIG.repositoryUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground"
            >
              GitHub
            </a>
            <a
              href={SITE_CONFIG.releasesUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground"
            >
              Releases
            </a>
            <a
              href={SITE_CONFIG.checksumUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground"
            >
              SHA-256
            </a>
          </div>
        </RailSection>
      </footer>
    </div>
  );
}
