import { ArrowUpRight, Download } from "lucide-react";
import { DashedHorizontalRule } from "@/components/rail-frame";
import { Button } from "@/components/ui/button";
import { SITE_CONFIG } from "@/config/site";

export function HeroCard() {
  return (
    <section className="relative z-10 w-full px-2 pt-[58px] md:pt-[72px]">
      <div className="relative mx-auto w-full max-w-[1480px] py-2 md:py-2.5">
        <DashedHorizontalRule className="hidden md:block -top-2" />

        <div className="cf-shadow-stack relative isolate flex min-h-[430px] items-center justify-center overflow-hidden rounded-xl bg-cf-accent px-6 py-10 md:min-h-[470px] md:rounded-2xl md:px-10 md:py-12">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 z-0"
          >
            <div
              className="absolute inset-0"
              style={{
                background:
                  "radial-gradient(ellipse 62% 34% at 50% 106%, rgb(255 244 204 / 0.85) 0%, rgb(255 186 92 / 0.42) 34%, rgb(255 94 31 / 0) 74%)",
              }}
            />
            <div className="cf-hero-halftone absolute inset-0" />
          </div>

          <div className="relative z-10 flex w-full max-w-[1080px] flex-col items-start gap-5 text-left md:items-center md:gap-6 md:text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/12 px-3 py-1 font-mono text-xs text-white/95 backdrop-blur-sm">
              v{SITE_CONFIG.version} · {SITE_CONFIG.platformLabel} ·{" "}
              {SITE_CONFIG.installerSizeLabel}
            </span>

            <h1 className="max-w-[980px] text-[38px] leading-[1.01] font-medium tracking-[-0.025em] text-white text-balance md:text-[56px] md:leading-[0.99] md:tracking-[-1.4px]">
              {SITE_CONFIG.hero.title}
            </h1>

            <p className="max-w-[660px] text-[16px] leading-[1.35] tracking-[-0.015em] text-white/92 md:text-[19.2px] md:leading-[1.25] md:tracking-[-0.48px]">
              {SITE_CONFIG.hero.subtitle}
            </p>

            <div className="flex w-full flex-col gap-3 pt-1 sm:w-auto sm:flex-row sm:items-center">
              <Button
                asChild
                className="h-auto w-full rounded-xl border border-white bg-white px-6 py-3.5 text-[16px] font-medium text-cf-ink hover:bg-white/90 sm:w-auto md:rounded-full md:py-3"
              >
                <a href={SITE_CONFIG.downloadUrl}>
                  <Download data-icon="inline-start" />
                  {SITE_CONFIG.hero.primaryCtaLabel}
                </a>
              </Button>

              <Button
                asChild
                variant="outline"
                className="h-auto w-full rounded-xl border border-white/35 bg-white/12 px-5 py-3.5 text-[15px] font-medium text-white hover:bg-white/20 hover:text-white sm:w-auto md:rounded-full md:py-3"
              >
                <a
                  href={SITE_CONFIG.releasesUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {SITE_CONFIG.hero.secondaryCtaLabel}
                  <ArrowUpRight data-icon="inline-end" />
                </a>
              </Button>
            </div>

            <p className="font-mono text-xs text-white/90">
              Self-contained Inno Setup installer ·{" "}
              <a
                href={SITE_CONFIG.checksumUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="whitespace-nowrap underline decoration-white/60 underline-offset-4 transition-colors hover:text-white"
              >
                Verify SHA-256
              </a>
            </p>
          </div>
        </div>

        <DashedHorizontalRule className="hidden md:block -bottom-2.5" />
      </div>
    </section>
  );
}
