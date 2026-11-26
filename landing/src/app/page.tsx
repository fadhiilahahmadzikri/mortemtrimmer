import { Button } from "@/components/ui/button";
import { SITE_CONFIG } from "@/config/site";

export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <section className="flex max-w-xl flex-col items-center gap-6 text-center">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          {SITE_CONFIG.name}
        </h1>
        <p className="text-muted-foreground text-base leading-relaxed">
          {SITE_CONFIG.tagline}
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Button asChild size="lg">
            <a
              href={SITE_CONFIG.releasesUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              Download Release
            </a>
          </Button>
          <Button asChild variant="outline" size="lg">
            <a
              href={SITE_CONFIG.repositoryUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub Repository
            </a>
          </Button>
        </div>
      </section>
    </main>
  );
}
