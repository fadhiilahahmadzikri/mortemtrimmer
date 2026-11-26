import type { ReactNode } from "react";
import { cn } from "cn";

export function DotBackdrop() {
  return (
    <svg
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0 h-full w-full"
    >
      <defs>
        <pattern
          id="cf-dot-matrix"
          x="0"
          y="0"
          width="12"
          height="12"
          patternUnits="userSpaceOnUse"
        >
          <circle cx="6" cy="6" r="0.75" fill="var(--cf-dots)" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#cf-dot-matrix)" />
    </svg>
  );
}

export function DashedHorizontalRule({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      preserveAspectRatio="none"
      className={cn(
        "pointer-events-none h-[1px] w-[200dvw] -translate-x-1/2 left-1/2 relative block",
        className
      )}
    >
      <line
        x1="0"
        y1="0.5"
        x2="100%"
        y2="0.5"
        stroke="var(--border)"
        strokeWidth="1"
        strokeDasharray="16,16"
      />
    </svg>
  );
}

export function CornerAnchorSquares() {
  const nodeClass =
    "bg-background border border-border rounded-[3px] absolute size-[14px]";
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 z-10 select-none"
    >
      <div className={cn(nodeClass, "-top-[7px] -left-[7px]")} />
      <div className={cn(nodeClass, "-top-[7px] -right-[7px]")} />
      <div className={cn(nodeClass, "-bottom-[7px] -left-[7px]")} />
      <div className={cn(nodeClass, "-bottom-[7px] -right-[7px]")} />
    </div>
  );
}

export function RailSection({
  id,
  children,
  className,
}: {
  id?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      id={id}
      className={cn(
        "relative z-10 mx-auto w-full max-w-[1200px] border-x border-dashed border-border",
        className
      )}
    >
      {children}
    </section>
  );
}
