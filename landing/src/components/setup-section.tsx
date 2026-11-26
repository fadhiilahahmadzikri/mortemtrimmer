"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, Check, Copy, Terminal } from "lucide-react";
import { WindowsMark } from "@/components/brand-marks";
import {
  CornerAnchorSquares,
  RailSection,
} from "@/components/rail-frame";
import { Button } from "@/components/ui/button";
import { SITE_CONFIG } from "@/config/site";

function CopyCommandRow({
  label,
  command,
}: {
  label: string;
  command: string;
}) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 1800);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="flex flex-col gap-1.5 rounded-lg border border-border bg-cf-surface-muted p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] text-muted-foreground">
          {label}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          aria-label={`Copy command: ${label}`}
          className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground transition-colors hover:bg-background hover:text-foreground"
        >
          {copied ? (
            <>
              <Check className="size-3 text-cf-accent" />
              Copied
            </>
          ) : (
            <>
              <Copy className="size-3" />
              Copy
            </>
          )}
        </button>
      </div>
      <code className="overflow-x-auto font-mono text-[12px] leading-relaxed text-foreground whitespace-nowrap">
        {command}
      </code>
    </div>
  );
}

export function SetupSection() {
  return (
    <RailSection id="setup" className="pb-8 md:pb-10">
      <div className="relative grid grid-cols-1 border-y border-border bg-background md:grid-cols-2">
        <CornerAnchorSquares />

        <div className="flex min-w-0 flex-col justify-between gap-6 border-b border-border p-6 md:border-r md:border-b-0 md:p-8">
          <div className="flex flex-col gap-2.5">
            <span className="font-mono text-xs uppercase tracking-widest text-cf-accent">
              Ready to run
            </span>
            <h2 className="text-[22px] font-medium tracking-[-0.02em] text-foreground">
              {SITE_CONFIG.customSetup.prebuiltTitle}
            </h2>
            <p className="text-[14px] leading-relaxed text-muted-foreground">
              {SITE_CONFIG.customSetup.prebuiltDescription}
            </p>
          </div>

          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <Button
                asChild
                size="lg"
                className="rounded-full border border-cf-accent bg-cf-accent px-6 text-[15px] font-medium text-white hover:border-cf-accent-hover hover:bg-cf-accent-hover"
              >
                <a href={SITE_CONFIG.downloadUrl}>
                  <WindowsMark data-icon="inline-start" />
                  {SITE_CONFIG.hero.primaryCtaLabel}
                </a>
              </Button>

              <Button
                asChild
                variant="outline"
                size="lg"
                className="rounded-full px-5 text-[14px]"
              >
                <a
                  href={SITE_CONFIG.releasesUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Release Notes
                  <ArrowUpRight data-icon="inline-end" />
                </a>
              </Button>
            </div>

            <p className="font-mono text-xs text-muted-foreground">
              v{SITE_CONFIG.version} · {SITE_CONFIG.platformLabel} ·{" "}
              {SITE_CONFIG.installerSizeLabel} ·{" "}
              <a
                href={SITE_CONFIG.checksumUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-foreground underline decoration-border underline-offset-4 hover:decoration-foreground"
              >
                Verify SHA-256
              </a>
            </p>
          </div>
        </div>

        <div className="flex min-w-0 flex-col justify-between gap-5 p-6 md:p-8">
          <div className="flex flex-col gap-2">
            <span className="inline-flex items-center gap-1.5 font-mono text-xs uppercase tracking-widest text-muted-foreground">
              <Terminal className="size-3.5" />
              Custom setup
            </span>
            <h2 className="text-[22px] font-medium tracking-[-0.02em] text-foreground">
              {SITE_CONFIG.customSetup.customTitle}
            </h2>
            <p className="text-[14px] leading-relaxed text-muted-foreground">
              {SITE_CONFIG.customSetup.customDescription}
            </p>
          </div>

          <div className="flex flex-col gap-2.5">
            {SITE_CONFIG.customSetup.commands.map((cmd) => (
              <CopyCommandRow
                key={cmd.id}
                label={cmd.label}
                command={cmd.command}
              />
            ))}
          </div>

          <div>
            <a
              href={SITE_CONFIG.docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-mono text-xs text-foreground underline decoration-border underline-offset-4 hover:decoration-foreground"
            >
              Read full CLI & source documentation
              <ArrowUpRight className="size-3.5" />
            </a>
          </div>
        </div>
      </div>
    </RailSection>
  );
}
