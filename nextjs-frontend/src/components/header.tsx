"use client";

import { useEffect, useState } from "react";
import { FlaskConical, Wifi, WifiOff } from "lucide-react";
import { checkHealth } from "@/services/api";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";

export function Header() {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = () =>
      checkHealth()
        .then(() => !cancelled && setHealthy(true))
        .catch(() => !cancelled && setHealthy(false));

    check();
    const id = setInterval(check, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <header className="sticky top-0 z-40 glass border-b border-[var(--border)]">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Left: Logo */}
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--primary)] text-[var(--primary-foreground)]">
            <FlaskConical className="h-4 w-4" />
          </div>
          <span className="font-semibold text-sm hidden sm:inline">
            AI Paper Generator
          </span>
        </div>

        {/* Right: Health + Theme */}
        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <div>
                {healthy === null && (
                  <Badge variant="secondary" className="gap-1">
                    <Wifi className="h-3 w-3 animate-pulse" /> Checking…
                  </Badge>
                )}
                {healthy === true && (
                  <Badge variant="success" className="gap-1">
                    <Wifi className="h-3 w-3" /> API Online
                  </Badge>
                )}
                {healthy === false && (
                  <Badge variant="destructive" className="gap-1">
                    <WifiOff className="h-3 w-3" /> API Offline
                  </Badge>
                )}
              </div>
            </TooltipTrigger>
            <TooltipContent>Backend API status (port 8000)</TooltipContent>
          </Tooltip>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
