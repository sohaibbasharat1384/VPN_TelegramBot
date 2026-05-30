"use client";

import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="h-9 w-9" />;
  const dark = theme === "dark";
  return (
    <button
      onClick={() => setTheme(dark ? "light" : "dark")}
      className="flex h-9 w-9 items-center justify-center rounded-md border border-border hover:bg-muted"
      aria-label="تغییر تم"
    >
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
