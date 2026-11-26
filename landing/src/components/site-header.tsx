"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { cn } from "cn";
import { Download } from "lucide-react";
import { GitHubMark } from "@/components/brand-marks";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { SITE_CONFIG } from "@/config/site";

export function SiteHeader() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const updateScroll = () => {
      setScrolled(window.scrollY > 12);
    };
    updateScroll();
    window.addEventListener("scroll", updateScroll, { passive: true });
    return () => window.removeEventListener("scroll", updateScroll);
  }, []);

  return (
    <header
      className={cn(
        "fixed top-0 right-0 left-0 z-50 h-[56px] transition-[background-color,border-color,backdrop-filter,box-shadow] duration-200 md:h-[72px]",
        scrolled
          ? "border-b border-border bg-cf-glass backdrop-blur-xl shadow-[0_1px_16px_rgb(0_0_0/0.05)] dark:shadow-[0_1px_16px_rgb(0_0_0/0.35)]"
          : "border-b border-border bg-cf-glass backdrop-blur-md md:border-transparent md:bg-transparent md:backdrop-blur-none"
      )}
    >
      <div className="mx-auto flex h-full w-full max-w-[1480px] items-center justify-between px-4 md:grid md:grid-cols-[1fr_auto_1fr] md:px-6">
        <a
          href="#"
          className="inline-flex items-center justify-self-start transition-opacity hover:opacity-85"
        >
          <Image
            src={SITE_CONFIG.logoPath}
            alt={SITE_CONFIG.name}
            width={SITE_CONFIG.logoWidth}
            height={SITE_CONFIG.logoHeight}
            className="h-9 w-auto object-contain md:h-11 dark:drop-shadow-[0_1px_10px_rgba(255,130,50,0.22)]"
            priority
          />
          <span className="sr-only">{SITE_CONFIG.name}</span>
        </a>

        <nav
          aria-label="Primary"
          className="hidden items-center gap-1 md:flex md:justify-self-center"
        >
          {SITE_CONFIG.navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              {...(item.external
                ? { target: "_blank", rel: "noopener noreferrer" }
                : {})}
              className="rounded-md px-3 py-1.5 text-[15px] font-medium text-foreground transition-colors hover:bg-muted"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2 justify-self-end">
          <ThemeToggle />

          <Button
            asChild
            variant="outline"
            className="hidden rounded-full border-border bg-background/70 px-4 text-[14px] font-medium text-foreground backdrop-blur-md hover:bg-muted sm:inline-flex"
          >
            <a
              href={SITE_CONFIG.repositoryUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              <GitHubMark data-icon="inline-start" />
              GitHub
            </a>
          </Button>

          <Button
            asChild
            className="rounded-full border border-cf-accent bg-cf-accent px-4 text-[14px] font-medium text-white hover:border-cf-accent-hover hover:bg-cf-accent-hover"
          >
            <a href={SITE_CONFIG.downloadUrl}>
              <Download data-icon="inline-start" />
              Download
            </a>
          </Button>
        </div>
      </div>
    </header>
  );
}
