"use client";

import { useCallback, useEffect } from "react";
import { AlertTriangle, CheckCircle2, Download } from "lucide-react";
import { getTaskStatus, getValidation } from "@/services/api";
import { usePaperStore } from "@/store/paper-store";
import { usePolling } from "@/hooks/use-polling";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PipelineSteps } from "./pipeline-steps";
import type { PipelineStage } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Determine current stage from stages dictionary. */
function stagestoStage(stages: Record<string, string> | undefined): PipelineStage {
  if (!stages) return "model_selection";
  
  // Check stages in order of pipeline
  const stageOrder: Array<[string, PipelineStage]> = [
    ["model_selection", "model_selection"],
    ["research", "research"],
    ["synthesis", "synthesis"],
    ["writing", "writing"],
    ["formatting", "formatting"],
    ["validation", "validation"],
    ["review", "review"],
    ["enhancement", "enhancement"],
  ];
  
  for (const [stageName, stagePipeline] of stageOrder) {
    if (stages[stageName] === "completed") {
      continue; // Move to next stage
    } else if (stages[stageName] === "processing" || stages[stageName] === "in_progress") {
      return stagePipeline;
    }
  }
  
  return "complete";
}

export function GenerationDashboard() {
  const {
    taskId,
    status,
    currentStage,
    validationReport,
    reviewReport,
    readyForSubmission,
    setStatus,
    setValidation,
    setCurrentStage,
    setValidationReport,
    setReviewReport,
  } = usePaperStore();

  const isActive =
    !!taskId &&
    status?.status !== "completed" &&
    status?.status !== "failed";

  const poll = useCallback(async () => {
    if (!taskId) return;
    try {
      const data = await getTaskStatus(taskId);
      setStatus(data);

      // Derive stage from stages dictionary
      if (data.status === "completed") {
        setCurrentStage("complete");
        // Extract new result fields
        if (data.result?.validation_report) setValidationReport(data.result.validation_report);
        if (data.result?.review_report) setReviewReport(data.result.review_report);
        // Fetch full validation
        try {
          const val = await getValidation(taskId);
          setValidation(val);
        } catch {}
      } else if (data.status === "failed") {
        setCurrentStage("failed");
      } else if (data.step) {
        setCurrentStage(data.step as PipelineStage);
      } else if (data.stages) {
        setCurrentStage(stagestoStage(data.stages));
      }
    } catch {
      // silently retry on next tick
    }
  }, [taskId, setStatus, setValidation, setCurrentStage, setValidationReport, setReviewReport]);

  usePolling(poll, 2000, isActive);

  // Also fetch once when status turns completed
  useEffect(() => {
    if (status?.status === "completed" && taskId) {
      getValidation(taskId).then(setValidation).catch(() => {});
    }
  }, [status?.status, taskId, setValidation]);

  const handleDownload = async (format: "pdf" | "docx" | "latex") => {
    if (!taskId) return;
    const endpointMap: Record<string, string> = {
      pdf:   `/api/langgraph/download/${taskId}`,
      docx:  `/api/langgraph/export/docx/${taskId}`,
      latex: `/api/langgraph/export/latex/${taskId}`,
    };
    const res = await fetch(`${API_BASE}${endpointMap[format]}`);
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `paper.${format === "latex" ? "tex" : format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!taskId) return null;

  const progress = status?.progress ?? 0;
  const isDone = status?.status === "completed";
  const isFailed = status?.status === "failed";

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Generation Pipeline</CardTitle>
          {isDone && (
            <Badge variant="success">
              <CheckCircle2 className="h-3 w-3 mr-1" /> Complete
            </Badge>
          )}
          {isFailed && (
            <Badge variant="destructive">
              <AlertTriangle className="h-3 w-3 mr-1" /> Failed
            </Badge>
          )}
          {!isDone && !isFailed && (
            <Badge variant="secondary">{Math.round(progress)}%</Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* Progress bar */}
        <div className="space-y-1">
          <Progress value={progress} />
          <p className="text-xs text-[var(--muted-foreground)]">
            {status?.message ?? "Initializing…"}
          </p>
        </div>

        {/* Pipeline steps */}
        <PipelineSteps />

        {/* Error */}
        {isFailed && status?.error && (
          <div className="rounded-lg border border-[var(--destructive)]/30 bg-[var(--destructive)]/5 p-3 text-sm text-[var(--destructive)]">
            {status.error}
          </div>
        )}

        {/* Download buttons */}
        {isDone && (
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => handleDownload("pdf")} className="gap-1.5">
              <Download className="h-4 w-4" /> Download PDF
            </Button>
            <Button size="sm" variant="secondary" onClick={() => handleDownload("docx")} className="gap-1.5">
              <Download className="h-4 w-4" /> Download DOCX
            </Button>
            <Button size="sm" variant="secondary" onClick={() => handleDownload("latex")} className="gap-1.5">
              <Download className="h-4 w-4" /> Download LaTeX (.tex)
            </Button>
          </div>
        )}

        {/* Per-section validation scores */}
        {isDone && validationReport && (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold">Section Quality Scores</h3>
            {Object.entries(validationReport.sections).map(([section, result]) => (
              <div key={section} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="capitalize">{section.replace(/_/g, " ")}</span>
                  <span className="font-medium">{(result.score * 100).toFixed(0)}%</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-[var(--border)]">
                  <div
                    className={`h-full rounded-full ${
                      result.passed ? "bg-emerald-500" : "bg-red-400"
                    }`}
                    style={{ width: `${result.score * 100}%` }}
                  />
                </div>
                {result.issues.map((issue) => (
                  <p key={issue} className="text-xs text-red-500">{issue}</p>
                ))}
              </div>
            ))}
          </div>
        )}

        {/* AI Reviewer panel */}
        {isDone && reviewReport && !reviewReport.skipped && (
          <div className="rounded-lg border border-[var(--border)] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">AI Reviewer Assessment</h3>
              {readyForSubmission ? (
                <Badge variant="success">✓ Ready for Submission</Badge>
              ) : (
                <Badge variant="warning">⚠ Needs Revision</Badge>
              )}
            </div>
            <p className="text-sm">
              Quality:{" "}
              <strong className="capitalize">
                {reviewReport.overall_quality.replace(/_/g, " ")}
              </strong>{" "}
              ({(reviewReport.score * 100).toFixed(0)}%)
            </p>
            {reviewReport.strengths.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold mb-1">Strengths</h4>
                <ul className="space-y-0.5 text-xs text-[var(--muted-foreground)]">
                  {reviewReport.strengths.map((s) => (
                    <li key={s}>✓ {s}</li>
                  ))}
                </ul>
              </div>
            )}
            {reviewReport.suggestions.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold mb-1">Suggestions</h4>
                <ul className="space-y-0.5 text-xs text-[var(--muted-foreground)]">
                  {reviewReport.suggestions.map((s) => (
                    <li key={s}>→ {s}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
