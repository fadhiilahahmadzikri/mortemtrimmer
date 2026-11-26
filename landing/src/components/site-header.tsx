import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SITE_CONFIG } from "@/config/site";

function GitHubMark() {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden="true"
      data-icon="inline-start"
    >
      <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z" />
    </svg>
  );
}

function MortemMark() {
  return (
    <svg
      viewBox="0 0 28 24"
      aria-hidden="true"
      className="h-5 w-auto shrink-0"
      fill="none"
    >
      <rect x="0" y="9" width="3" height="6" rx="1.5" fill="var(--cf-accent)" />
      <rect x="5" y="4" width="3" height="16" rx="1.5" fill="var(--cf-accent)" />
      <rect x="10" y="1" width="3" height="22" rx="1.5" fill="var(--cf-accent)" />
      <path
        d="M16 12h2m2-6v12m4-8v4"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function SiteHeader() {
  return (
    <header className="fixed top-0 right-0 left-0 z-50 h-[54px] bg-background/90 backdrop-blur-md border-b border-border md:h-[72px] md:bg-transparent md:border-b-0 md:backdrop-blur-none">
      <div className="mx-auto flex h-full w-full max-w-[1480px] items-center justify-between px-4 md:grid md:grid-cols-[1fr_auto_1fr] md:px-6">
        <a
          href="#"
          className="inline-flex items-center gap-2.5 justify-self-start text-foreground transition-opacity hover:opacity-80"
        >
          <MortemMark />
          <span className="text-[13px] font-bold tracking-[0.08em]">
            {SITE_CONFIG.wordmark}
          </span>
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
          <Button
            asChild
            variant="outline"
            className="hidden h-[36px] rounded-full border-border bg-background/85 px-3.5 text-[14px] font-medium text-foreground backdrop-blur-md hover:bg-muted sm:inline-flex"
          >
            <a
              href={SITE_CONFIG.repositoryUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              <GitHubMark />
              GitHub
            </a>
          </Button>
          <Button
            asChild
            className="h-[36px] rounded-full border border-cf-accent bg-cf-accent px-3.5 text-[14px] font-medium text-white hover:border-cf-accent-hover hover:bg-cf-accent-hover"
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
