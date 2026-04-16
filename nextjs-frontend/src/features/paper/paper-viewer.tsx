"use client";

import { usePaperStore } from "@/store/paper-store";
import { SectionEditor } from "./section-editor";
import { PaperPreview } from "./paper-preview";
import { IEEEPreview } from "@/components/ieee-preview";

export function PaperViewer() {
  const status = usePaperStore((s) => s.status);

  if (!status || status.status === "pending") return null;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-[600px]">
        <SectionEditor />
        <PaperPreview />
      </div>
      
      {status.task_id && (
        <IEEEPreview taskId={status.task_id} status={status} />
      )}
    </div>
  );
}
