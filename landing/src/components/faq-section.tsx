import {
  CornerAnchorSquares,
  RailSection,
} from "@/components/rail-frame";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { SITE_CONFIG } from "@/config/site";

export function FaqSection() {
  return (
    <RailSection id="faq" className="pb-6 md:pb-8">
      <div className="relative grid grid-cols-1 border-y border-border bg-background lg:grid-cols-[5fr_7fr]">
        <CornerAnchorSquares />

        <div className="flex flex-col gap-3 border-b border-border p-6 md:p-8 lg:border-r lg:border-b-0">
          <p className="font-mono text-xs uppercase tracking-widest text-cf-accent">
            FAQ
          </p>
          <h2 className="text-[26px] leading-[1.15] font-medium tracking-[-0.02em] text-foreground md:text-[32px]">
            Frequently asked questions
          </h2>
          <p className="max-w-sm text-[15px] leading-relaxed text-muted-foreground">
            Everything you need to know about automating offline video silence
            trimming, Windows integration, and safety checks.
          </p>
        </div>

        <div className="p-4 md:p-6">
          <Accordion type="single" collapsible className="w-full">
            {SITE_CONFIG.faq.map((item) => (
              <AccordionItem key={item.id} value={item.id} className="px-2">
                <AccordionTrigger className="py-4 text-[15px] font-medium text-foreground hover:no-underline hover:text-cf-accent">
                  {item.question}
                </AccordionTrigger>
                <AccordionContent className="pb-4 text-[14px] leading-relaxed text-muted-foreground">
                  {item.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </RailSection>
  );
}
