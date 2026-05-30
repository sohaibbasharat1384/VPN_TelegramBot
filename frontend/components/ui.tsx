"use client";

import { type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "ghost" | "danger" | "success" | "outline";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-primary text-primary-foreground hover:opacity-90",
  success: "bg-success text-white hover:opacity-90",
  danger: "bg-danger text-white hover:opacity-90",
  ghost: "bg-transparent hover:bg-muted",
  outline: "border border-border bg-transparent hover:bg-muted",
};

export function Button({
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition disabled:opacity-50 disabled:pointer-events-none",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-md border border-border bg-card px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/40",
        className,
      )}
      {...props}
    />
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("rounded-lg border border-border bg-card p-5 shadow-sm", className)}>
      {children}
    </div>
  );
}

export function Badge({ children, tone = "muted" }: { children: ReactNode; tone?: string }) {
  const tones: Record<string, string> = {
    muted: "bg-muted text-muted-foreground",
    success: "bg-success/15 text-success",
    danger: "bg-danger/15 text-danger",
    warning: "bg-warning/15 text-warning",
    primary: "bg-primary/15 text-primary",
  };
  return (
    <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium", tones[tone] ?? tones.muted)}>
      {children}
    </span>
  );
}

export function Spinner() {
  return (
    <div className="flex justify-center py-10">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    </div>
  );
}

export function Table({ head, children }: { head: ReactNode; children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-right text-sm">
        <thead className="bg-muted/60 text-muted-foreground">{head}</thead>
        <tbody className="divide-y divide-border">{children}</tbody>
      </table>
    </div>
  );
}

export function Th({ children }: { children: ReactNode }) {
  return <th className="px-4 py-3 font-medium">{children}</th>;
}

export function Td({ children, className }: { children: ReactNode; className?: string }) {
  return <td className={cn("px-4 py-3", className)}>{children}</td>;
}
