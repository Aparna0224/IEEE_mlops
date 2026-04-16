import { create } from "zustand";
import type {
  TaskStatus,
  FullValidationResponse,
  PipelineStage,
  ValidationReport,
  ReviewReport,
} from "@/types";

interface PaperState {
  /* ── Generation ── */
  taskId: string | null;
  status: TaskStatus | null;
  validation: FullValidationResponse | null;
  currentStage: PipelineStage;

  /* ── New agent outputs ── */
  validationReport: ValidationReport | null;
  reviewReport: ReviewReport | null;
  reviewScore: number;
  readyForSubmission: boolean;
  docxPath: string | null;

  /* ── Paper editor ── */
  editedSections: Record<string, string>;

  /* ── UI ── */
  activeTab: "editor" | "metrics" | "reviewer";

  /* ── Actions ── */
  setTaskId: (id: string | null) => void;
  setStatus: (s: TaskStatus) => void;
  setValidation: (v: FullValidationResponse) => void;
  setCurrentStage: (stage: PipelineStage) => void;
  setEditedSection: (name: string, text: string) => void;
  resetEditedSections: () => void;
  setActiveTab: (tab: "editor" | "metrics" | "reviewer") => void;
  setValidationReport: (report: ValidationReport) => void;
  setReviewReport: (report: ReviewReport) => void;
  reset: () => void;
}

export const usePaperStore = create<PaperState>((set) => ({
  taskId: null,
  status: null,
  validation: null,
  currentStage: "pending",
  validationReport: null,
  reviewReport: null,
  reviewScore: 0,
  readyForSubmission: false,
  docxPath: null,
  editedSections: {},
  activeTab: "editor",

  setTaskId: (id) => set({ taskId: id }),
  setStatus: (s) => set({ status: s }),
  setValidation: (v) => set({ validation: v }),
  setCurrentStage: (stage) => set({ currentStage: stage }),
  setEditedSection: (name, text) =>
    set((state) => ({
      editedSections: { ...state.editedSections, [name]: text },
    })),
  resetEditedSections: () => set({ editedSections: {} }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setValidationReport: (report) => set({ validationReport: report }),
  setReviewReport: (report) =>
    set({
      reviewReport: report,
      reviewScore: report.score,
      readyForSubmission: report.ready_for_submission,
    }),
  reset: () =>
    set({
      taskId: null,
      status: null,
      validation: null,
      currentStage: "pending",
      validationReport: null,
      reviewReport: null,
      reviewScore: 0,
      readyForSubmission: false,
      docxPath: null,
      editedSections: {},
      activeTab: "editor",
    }),
}));
