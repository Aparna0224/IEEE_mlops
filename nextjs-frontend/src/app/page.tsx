"use client";

import { usePaperStore } from "@/store/paper-store";
import { Header } from "@/components/header";
import { TopicInput } from "@/features/paper/topic-input";
import { GenerationDashboard } from "@/features/dashboard/generation-dashboard";
import { PaperViewer } from "@/features/paper/paper-viewer";
import { QualityMetrics } from "@/features/dashboard/quality-metrics";
import { ReviewerFeedback } from "@/features/dashboard/reviewer-feedback";
import { ExportButtons } from "@/features/paper/export-buttons";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export default function Home() {
  const { taskId, status, activeTab, setActiveTab } = usePaperStore();

  const isGenerating =
    !!taskId && status?.status !== "completed" && status?.status !== "failed";
  const isComplete = status?.status === "completed";

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 py-8 space-y-8">
        {/* ── Topic Input (always visible when no task running) ── */}
        {!taskId && <TopicInput />}

        {/* ── Generation Dashboard (visible during generation) ── */}
        {taskId && <GenerationDashboard />}

        {/* ── Tabbed workspace (appears once generation starts) ── */}
        {taskId && (isGenerating || isComplete) && (
          <Tabs
            value={activeTab}
            onValueChange={(v) =>
              setActiveTab(v as "editor" | "metrics" | "reviewer")
            }
          >
            <TabsList>
              <TabsTrigger value="editor">Paper Editor</TabsTrigger>
              <TabsTrigger value="metrics">Quality Metrics</TabsTrigger>
              <TabsTrigger value="reviewer">AI Reviewer</TabsTrigger>
            </TabsList>

            <TabsContent value="editor">
              <div className="space-y-4">
                <PaperViewer />
                <ExportButtons />
              </div>
            </TabsContent>

            <TabsContent value="metrics">
              <QualityMetrics />
            </TabsContent>

            <TabsContent value="reviewer">
              {status?.enhancement_scores?.novelty_analysis ? (
                <ReviewerFeedback />
              ) : (
                <p className="text-sm text-muted-foreground py-6 text-center">
                  Waiting for analysis to complete...
                </p>
              )}
            </TabsContent>
          </Tabs>
        )}

        {/* ── New Paper button (when task is done) ── */}
        {(isComplete || status?.status === "failed") && (
          <div className="flex justify-center pt-4">
            <button
              className="text-sm text-[var(--primary)] hover:underline cursor-pointer"
              onClick={() => usePaperStore.getState().reset()}
            >
              ← Generate another paper
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--border)] py-4 text-center text-xs text-[var(--muted-foreground)]">
        AI Research Paper Generator — Multi-Agent Pipeline with IEEE Compliance
      </footer>
    </div>
  );
}
