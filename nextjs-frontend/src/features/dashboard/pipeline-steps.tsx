"use client";

import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { PIPELINE_STEPS, type PipelineStage } from "@/types";
import { usePaperStore } from "@/store/paper-store";

const stageOrder = PIPELINE_STEPS.map((s) => s.id);

function getStepState(
  stepId: string,
  current: PipelineStage
): "complete" | "active" | "upcoming" | "failed" {
  if (current === "failed") {
    const currentIdx = stageOrder.indexOf(current);
    const stepIdx = stageOrder.indexOf(stepId);
    if (stepIdx < currentIdx) return "complete";
    if (stepIdx === currentIdx) return "failed";
    return "upcoming";
  }
  // When pipeline is done, every step (including "complete") is finished
  if (current === "complete") return "complete";

  const currentIdx = stageOrder.indexOf(current);
  const stepIdx = stageOrder.indexOf(stepId);
  if (currentIdx === -1) return "upcoming";
  if (stepIdx < currentIdx) return "complete";
  if (stepIdx === currentIdx) return "active";
  return "upcoming";
}

export function PipelineSteps() {
  const currentStage = usePaperStore((s) => s.currentStage);

  return (
    <div className="space-y-1">
      {PIPELINE_STEPS.map((step, i) => {
        const state = getStepState(step.id, currentStage);
        return (
          <div key={step.id} className="flex items-start gap-3">
            {/* Connector line + dot */}
            <div className="flex flex-col items-center">
              <div className="relative">
                {state === "complete" && (
                  <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                )}
                {state === "active" && (
                  <div className="relative">
                    <Loader2 className="h-5 w-5 text-[var(--primary)] animate-spin" />
                    <span className="absolute inset-0 rounded-full step-dot-pulse" />
                  </div>
                )}
                {state === "upcoming" && (
                  <Circle className="h-5 w-5 text-[var(--muted-foreground)]" />
                )}
                {state === "failed" && (
                  <XCircle className="h-5 w-5 text-[var(--destructive)]" />
                )}
              </div>
              {i < PIPELINE_STEPS.length - 1 && (
                <div
                  className={cn(
                    "w-px h-6 mt-1",
                    state === "complete"
                      ? "bg-emerald-500"
                      : "bg-[var(--border)]"
                  )}
                />
              )}
            </div>

            {/* Label */}
            <div className="pb-4">
              <p
                className={cn(
                  "text-sm font-medium leading-none",
                  state === "active" && "text-[var(--primary)]",
                  state === "complete" && "text-emerald-500",
                  state === "upcoming" && "text-[var(--muted-foreground)]",
                  state === "failed" && "text-[var(--destructive)]"
                )}
              >
                {step.label}
              </p>
              <p className="text-xs text-[var(--muted-foreground)] mt-0.5">
                {step.description}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
