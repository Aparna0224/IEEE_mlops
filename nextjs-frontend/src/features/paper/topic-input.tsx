"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Sparkles, Zap, FlaskConical, Plus, Trash2, Users, ChevronDown } from "lucide-react";
import { generatePaper } from "@/services/api";
import { usePaperStore } from "@/store/paper-store";
import { MODELS, type AuthorInfo, type EquationInfo, type DiagramInfo, type TableInfo } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectLabel,
  SelectGroup,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function TopicInput() {
  const [topic, setTopic] = useState("");
  const [notes, setNotes] = useState("");
  const [model, setModel] = useState(MODELS[0].value);
  const [maxResults, setMaxResults] = useState(5);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const emptyAuthor = (): AuthorInfo => ({ name: "", affiliation: "", location: "", email: "" });
  const emptyEquation = (): EquationInfo => ({ id: crypto.randomUUID(), label: "", notation: "", latex: "", description: "" });
  const emptyDiagram = (): DiagramInfo => ({ id: crypto.randomUUID(), label: "", caption: "", file: "" });
  const emptyTable = (): TableInfo => ({ id: crypto.randomUUID(), label: "", caption: "", headers: ["Model", "Accuracy"], rows: [["Baseline", "90%"], ["Proposed", "94%"]] });
  const [authors, setAuthors] = useState<AuthorInfo[]>([emptyAuthor()]);
  const [equations, setEquations] = useState<EquationInfo[]>([]);
  const [diagrams, setDiagrams] = useState<DiagramInfo[]>([]);
  const [tables, setTables] = useState<TableInfo[]>([]);
  const { setTaskId, setCurrentStage, reset } = usePaperStore();

  const updateAuthor = (idx: number, field: keyof AuthorInfo, value: string) => {
    setAuthors((prev) => prev.map((a, i) => (i === idx ? { ...a, [field]: value } : a)));
  };
  const addAuthor = () => {
    if (authors.length < 6) setAuthors((prev) => [...prev, emptyAuthor()]);
  };
  const removeAuthor = (idx: number) => {
    if (authors.length > 1) setAuthors((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateEquation = (idx: number, field: keyof EquationInfo, value: string) => {
    setEquations((prev) => prev.map((eq, i) => (i === idx ? { ...eq, [field]: value } : eq)));
  };
  const addEquation = () => setEquations((prev) => [...prev, emptyEquation()]);
  const removeEquation = (idx: number) => setEquations((prev) => prev.filter((_, i) => i !== idx));

  const updateDiagram = (idx: number, field: keyof DiagramInfo, value: string) => {
    setDiagrams((prev) => prev.map((dg, i) => (i === idx ? { ...dg, [field]: value } : dg)));
  };
  const addDiagram = () => setDiagrams((prev) => [...prev, emptyDiagram()]);
  const removeDiagram = (idx: number) => setDiagrams((prev) => prev.filter((_, i) => i !== idx));

  const updateTable = (idx: number, field: keyof TableInfo, value: string) => {
    setTables((prev) => prev.map((tb, i) => (i === idx ? { ...tb, [field]: value } : tb)));
  };
  const updateTableHeaders = (idx: number, value: string) => {
    const headers = value.split(",").map((h) => h.trim()).filter(Boolean);
    setTables((prev) => prev.map((tb, i) => (i === idx ? { ...tb, headers } : tb)));
  };
  const updateTableRows = (idx: number, value: string) => {
    const rows = value
      .split("\n")
      .map((line) => line.split(",").map((cell) => cell.trim()))
      .filter((row) => row.length > 0 && row.some(Boolean));
    setTables((prev) => prev.map((tb, i) => (i === idx ? { ...tb, rows } : tb)));
  };
  const addTable = () => setTables((prev) => [...prev, emptyTable()]);
  const removeTable = (idx: number) => setTables((prev) => prev.filter((_, i) => i !== idx));

  const mutation = useMutation({
    mutationFn: generatePaper,
    onSuccess: (data) => {
      setTaskId(data.task_id);
      setCurrentStage("research");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    reset();
    const cleanAuthors = authors
      .filter((a) => a.name.trim() || a.affiliation.trim() || a.email.trim() || a.location.trim())
      .map((a) => ({
        ...a,
        name: a.name.trim() || "Author",
        affiliation: a.affiliation.trim() || "Independent Researcher",
      }));

    const cleanEquations = equations
      .filter((eq) => eq.label.trim() || eq.notation.trim() || eq.latex?.trim() || eq.description?.trim())
      .map((eq, idx) => ({
        ...eq,
        label: eq.label.trim() || `eq:${idx + 1}`,
        notation: eq.notation.trim() || "custom_equation",
        latex: eq.latex?.trim() || undefined,
        description: eq.description?.trim() || undefined,
      }));

    const cleanDiagrams = diagrams
      .filter((dg) => dg.label.trim() || dg.caption.trim() || (typeof dg.file === "string" && dg.file.trim()))
      .map((dg, idx) => ({
        ...dg,
        label: dg.label.trim() || `fig:${idx + 1}`,
        caption: dg.caption.trim() || "Diagram",
        file: typeof dg.file === "string" ? dg.file.trim() : dg.file,
      }));

    const cleanTables = tables
      .filter((tb) => tb.caption.trim() || tb.label.trim() || tb.headers.length > 0 || tb.rows.length > 0)
      .map((tb, idx) => ({
        ...tb,
        label: tb.label.trim() || `tbl:${idx + 1}`,
        caption: tb.caption.trim() || "Model Performance Comparison",
        headers: tb.headers.length > 0 ? tb.headers : ["Metric", "Value"],
        rows: tb.rows.length > 0 ? tb.rows : [["Placeholder", "N/A"]],
      }));

    mutation.mutate({ 
      topic: topic.trim(), 
      notes: notes.trim() || undefined,
      max_references: maxResults, 
      model_name: model, 
      authors: cleanAuthors,
      diagrams: cleanDiagrams,
      equations: cleanEquations,
      tables: cleanTables,
    });
  };

  const freeModels = MODELS.filter((m) => m.tier === "free");
  const paidModels = MODELS.filter((m) => m.tier === "paid");

  return (
    <Card className="max-w-2xl mx-auto">
      <CardHeader className="text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--primary)]/10">
          <FlaskConical className="h-6 w-6 text-[var(--primary)]" />
        </div>
        <CardTitle className="text-2xl">AI Research Paper Generator</CardTitle>
        <CardDescription>
          Enter a research topic and our multi-agent pipeline will generate an
          IEEE-formatted paper with novelty enhancement and AI review.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Topic - MAIN FIELD */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Research Topic *</label>
            <Input
              placeholder="e.g. Quantum Computing in Machine Learning"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              required
              autoFocus
              className="text-base"
            />
          </div>

          {/* Quick Settings Row */}
          <div className="grid grid-cols-2 gap-4">
            {/* Model */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Model</label>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>Free Tier</SelectLabel>
                    {freeModels.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                  <SelectGroup>
                    <SelectLabel>Paid Tier</SelectLabel>
                    {paidModels.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>

            {/* Max papers */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Reference Papers</label>
              <Select
                value={String(maxResults)}
                onValueChange={(v) => setMaxResults(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[3, 5, 8, 10].map((n) => (
                    <SelectItem key={n} value={String(n)}>
                      {n} papers
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Advanced Options (Collapsible) */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-[var(--primary)] hover:underline"
          >
            <ChevronDown className={`h-4 w-4 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
            {showAdvanced ? "Hide" : "Show"} Advanced Options
          </button>

          {showAdvanced && (
            <>
              <Separator />

              <div className="space-y-2">
                <label className="text-sm font-medium">Research Notes</label>
                <Textarea
                  placeholder="Add methodology notes, dataset details, assumptions, constraints, expected contributions..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="min-h-[96px]"
                />
              </div>
              
              {/* ── Authors (1–6) ── */}
              <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] flex items-center gap-1.5">
                    <Users className="h-3.5 w-3.5" /> Authors ({authors.length}/6)
                  </p>
                  {authors.length < 6 && (
                    <Button type="button" variant="outline" size="sm" onClick={addAuthor}>
                      <Plus className="h-3.5 w-3.5" /> Add Author
                    </Button>
                  )}
                </div>

                {authors.map((author, idx) => (
                  <div key={idx} className="rounded-lg border border-[var(--border)] p-3 space-y-3 relative bg-white dark:bg-slate-950">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-[var(--muted-foreground)]">Author {idx + 1}</span>
                      {authors.length > 1 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-[var(--destructive)]"
                          onClick={() => removeAuthor(idx)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <Input
                        placeholder="Name (optional)"
                        value={author.name}
                        onChange={(e) => updateAuthor(idx, "name", e.target.value)}
                      />
                      <Input
                        type="email"
                        placeholder="Email (optional)"
                        value={author.email}
                        onChange={(e) => updateAuthor(idx, "email", e.target.value)}
                      />
                      <Input
                        placeholder="Affiliation (optional)"
                        value={author.affiliation}
                        onChange={(e) => updateAuthor(idx, "affiliation", e.target.value)}
                      />
                      <Input
                        placeholder="Location (optional)"
                        value={author.location}
                        onChange={(e) => updateAuthor(idx, "location", e.target.value)}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="rounded-lg border border-[var(--border)] p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                    Equations ({equations.length})
                  </p>
                  <Button type="button" variant="outline" size="sm" onClick={addEquation}>
                    <Plus className="h-3.5 w-3.5" /> Add Equation
                  </Button>
                </div>

                {equations.length === 0 && (
                  <p className="text-xs text-[var(--muted-foreground)]">No equations added yet.</p>
                )}

                {equations.map((eq, idx) => (
                  <div key={eq.id ?? idx} className="rounded-lg border border-[var(--border)] p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-[var(--muted-foreground)]">Equation {idx + 1}</span>
                      <Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0 text-[var(--destructive)]" onClick={() => removeEquation(idx)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <Input placeholder="Label (e.g., eq:loss)" value={eq.label} onChange={(e) => updateEquation(idx, "label", e.target.value)} />
                      <Input placeholder="Notation (e.g., cross entropy)" value={eq.notation} onChange={(e) => updateEquation(idx, "notation", e.target.value)} />
                    </div>
                    <Input placeholder="LaTeX (e.g., L = -\sum y_i \log(\hat{y_i}))" value={eq.latex ?? ""} onChange={(e) => updateEquation(idx, "latex", e.target.value)} />
                    <Input placeholder="Description (optional)" value={eq.description ?? ""} onChange={(e) => updateEquation(idx, "description", e.target.value)} />
                  </div>
                ))}
              </div>

              <div className="rounded-lg border border-[var(--border)] p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                    Diagrams ({diagrams.length})
                  </p>
                  <Button type="button" variant="outline" size="sm" onClick={addDiagram}>
                    <Plus className="h-3.5 w-3.5" /> Add Diagram
                  </Button>
                </div>

                {diagrams.length === 0 && (
                  <p className="text-xs text-[var(--muted-foreground)]">No diagrams added yet.</p>
                )}

                {diagrams.map((dg, idx) => (
                  <div key={dg.id ?? idx} className="rounded-lg border border-[var(--border)] p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-[var(--muted-foreground)]">Diagram {idx + 1}</span>
                      <Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0 text-[var(--destructive)]" onClick={() => removeDiagram(idx)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <Input placeholder="Label (e.g., fig:architecture)" value={dg.label} onChange={(e) => updateDiagram(idx, "label", e.target.value)} />
                      <Input placeholder="Caption" value={dg.caption} onChange={(e) => updateDiagram(idx, "caption", e.target.value)} />
                    </div>
                    <Input
                      placeholder="Diagram file path or URL (e.g., ./images/arch.png)"
                      value={typeof dg.file === "string" ? dg.file : ""}
                      onChange={(e) => updateDiagram(idx, "file", e.target.value)}
                    />
                  </div>
                ))}
              </div>

              <div className="rounded-lg border border-[var(--border)] p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                    Tables ({tables.length})
                  </p>
                  <Button type="button" variant="outline" size="sm" onClick={addTable}>
                    <Plus className="h-3.5 w-3.5" /> Add Table
                  </Button>
                </div>

                {tables.length === 0 && (
                  <p className="text-xs text-[var(--muted-foreground)]">No tables added yet.</p>
                )}

                {tables.map((tb, idx) => (
                  <div key={tb.id ?? idx} className="rounded-lg border border-[var(--border)] p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-[var(--muted-foreground)]">Table {idx + 1}</span>
                      <Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0 text-[var(--destructive)]" onClick={() => removeTable(idx)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <Input placeholder="Label (e.g., tbl:performance)" value={tb.label} onChange={(e) => updateTable(idx, "label", e.target.value)} />
                      <Input placeholder="Caption" value={tb.caption} onChange={(e) => updateTable(idx, "caption", e.target.value)} />
                    </div>
                    <Input
                      placeholder="Headers (comma-separated, e.g., Model, Accuracy)"
                      value={tb.headers.join(", ")}
                      onChange={(e) => updateTableHeaders(idx, e.target.value)}
                    />
                    <Textarea
                      placeholder={"Rows (one per line, comma-separated)\nCNN, 90%\nTransformer, 94%"}
                      value={tb.rows.map((r) => r.join(", ")).join("\n")}
                      onChange={(e) => updateTableRows(idx, e.target.value)}
                      className="min-h-[88px]"
                    />
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Error */}
          {mutation.isError && (
            <div className="p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded text-sm text-red-700 dark:text-red-200">
              ❌ Error: {(mutation.error as Error).message}
            </div>
          )}

          {/* Submit */}
          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={mutation.isPending || !topic.trim()}
          >
            {mutation.isPending ? (
              <>
                <Zap className="h-4 w-4 animate-pulse" />
                Starting Pipeline…
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Generate Paper
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
