"use client";

import { useState } from "react";
import {
  Download,
  FileJson,
  Copy,
  Check,
  FileText,
  FileCode,
  AlertCircle,
} from "lucide-react";
import { usePaperStore } from "@/store/paper-store";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";

export function ExportButtons() {
  const { taskId, status, editedSections } = usePaperStore();
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const isComplete = status?.status === "completed";

  const handleExport = async (format: "pdf" | "latex" | "json" | "txt") => {
    if (!taskId) return;

    try {
      setError(null);
      setDownloading(format);

      const endpoints: Record<string, string> = {
        pdf: `/api/langgraph/download/${taskId}`,
        latex: `/api/langgraph/export/latex/${taskId}`,
        json: `/api/langgraph/export/json/${taskId}`,
        txt: `/api/langgraph/export/txt/${taskId}`,
      };

      const response = await fetch(`${API_BASE}${endpoints[format]}`);

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail ?? `Export failed: ${response.status}`);
      }

      const contentDisposition = response.headers.get("content-disposition");
      let filename = `paper.${format === "latex" ? "tex" : format}`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^\"]+)"?/);
        if (match?.[1]) filename = match[1];
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Export failed";
      setError(message);
      console.error(`Export error (${format}):`, err);
    } finally {
      setDownloading(null);
    }
  };

  const handleCopyContent = async () => {
    const result = status?.result;
    let content = "";

    if (result) {
      const sections = [
        result.abstract,
        result.introduction,
        result.related_work,
        result.methodology,
        result.implementation,
        result.results,
        result.conclusion,
      ];
      content = sections.filter(Boolean).join("\n\n---\n\n");
    } else {
      content = Object.entries(editedSections)
        .map(([section, text]) => `## ${section}\n\n${text}`)
        .join("\n\n---\n\n");
    }

    if (!content) {
      setError("No content to copy");
      return;
    }

    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Failed to copy to clipboard");
    }
  };

  if (!isComplete) return null;

  return (
    <div className="space-y-3">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--card)] px-4 py-3">
        <span className="text-sm font-medium flex items-center gap-1.5">
          <Download className="h-4 w-4" /> Export Paper As:
        </span>

        <div className="flex flex-wrap gap-2 ml-auto">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                onClick={() => handleExport("pdf")}
                disabled={downloading === "pdf"}
                className="gap-1.5"
              >
                <Download className="h-4 w-4" />
                {downloading === "pdf" ? "Generating..." : "PDF"}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Download IEEE-formatted PDF document</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => handleExport("latex")}
                disabled={downloading === "latex"}
                className="gap-1.5"
              >
                <FileCode className="h-4 w-4" />
                {downloading === "latex" ? "Exporting..." : "LaTeX"}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Download .tex source for Overleaf/local editing</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => handleExport("json")}
                disabled={downloading === "json"}
                className="gap-1.5"
              >
                <FileJson className="h-4 w-4" />
                {downloading === "json" ? "Exporting..." : "JSON"}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Export complete paper data as JSON</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => handleExport("txt")}
                disabled={downloading === "txt"}
                className="gap-1.5"
              >
                <FileText className="h-4 w-4" />
                {downloading === "txt" ? "Exporting..." : "Text"}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Export as plain text for quick sharing</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button size="sm" variant="outline" onClick={handleCopyContent} className="gap-1.5">
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? "Copied!" : "Copy"}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Copy paper content to clipboard</TooltipContent>
          </Tooltip>
        </div>
      </div>
    </div>
  );
}
