import Image from "next/image";
import { WindowsMark } from "@/components/brand-marks";
import { DashedHorizontalRule } from "@/components/rail-frame";
import { Button } from "@/components/ui/button";
import { SITE_CONFIG } from "@/config/site";

export function HeroCard() {
  return (
    <section className="relative z-10 w-full px-2 pt-[60px] md:pt-[72px]">
      <div className="relative mx-auto w-full max-w-[1480px] py-2 md:py-2.5">
        <DashedHorizontalRule className="hidden md:block -top-2" />

        <div className="cf-shadow-stack relative isolate flex min-h-[450px] items-center overflow-hidden rounded-xl bg-[#160e09] px-6 py-12 ring-1 ring-inset ring-white/10 md:min-h-[520px] md:rounded-2xl md:px-10 md:py-16">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 z-0"
          >
            <Image
              src={SITE_CONFIG.heroBgPath}
              alt=""
              fill
              priority
              className="object-cover object-[78%_30%] select-none md:object-[72%_28%]"
            />
            <div
              className="absolute inset-0 md:hidden"
              style={{
                background:
                  "linear-gradient(180deg, rgb(14 9 6 / 0.72) 0%, rgb(16 10 6 / 0.62) 55%, rgb(16 10 6 / 0.80) 100%)",
              }}
            />
            <div
              className="absolute inset-0"
              style={{
                background:
                  "linear-gradient(90deg, rgb(15 9 6 / 0.90) 0%, rgb(18 11 7 / 0.72) 42%, rgb(22 12 7 / 0.24) 72%, rgb(255 94 31 / 0.08) 100%)",
              }}
            />
            <div
              className="absolute inset-0"
              style={{
                background:
                  "radial-gradient(ellipse 58% 40% at 70% 106%, rgb(255 94 31 / 0.32) 0%, rgb(255 150 64 / 0.14) 38%, rgb(255 94 31 / 0) 74%)",
              }}
            />
            <div className="cf-hero-halftone absolute inset-0 opacity-40" />
          </div>

          <div className="relative z-10 mx-auto w-full max-w-[1140px]">
            <div className="flex w-full max-w-[650px] flex-col items-start gap-6 text-left">
              <h1 className="text-[38px] leading-[1.01] font-medium tracking-[-0.025em] text-white text-balance md:text-[56px] md:leading-[0.99] md:tracking-[-1.4px]">
                {SITE_CONFIG.hero.title}
              </h1>

              <p className="max-w-[560px] text-[16px] leading-[1.4] tracking-[-0.015em] text-white/90 md:text-[19.2px] md:leading-[1.3] md:tracking-[-0.48px]">
                {SITE_CONFIG.hero.subtitle}
              </p>

              <div className="w-full pt-2 sm:w-auto">
                <Button
                  asChild
                  size="lg"
                  className="h-auto w-full rounded-xl border border-white bg-white px-7 py-3.5 text-[16px] font-medium text-cf-ink shadow-[0_8px_24px_rgb(0_0_0/0.35)] hover:bg-white/92 sm:w-auto md:rounded-full"
                >
                  <a href={SITE_CONFIG.downloadUrl}>
                    <WindowsMark data-icon="inline-start" />
                    {SITE_CONFIG.hero.primaryCtaLabel}
                  </a>
                </Button>
              </div>
            </div>
          </div>
        </div>

        <DashedHorizontalRule className="hidden md:block -bottom-2.5" />
      </div>
    </section>
  );
}
