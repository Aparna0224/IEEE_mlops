"use client";

import { useTheme } from "@/hooks/use-theme";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // This hook applies the dark class to the document
  useTheme();
  return <>{children}</>;
}
