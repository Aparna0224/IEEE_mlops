"use client";

import { usePaperStore } from "@/store/paper-store";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BookOpen } from "lucide-react";
import { IEEE_SECTIONS } from "@/types";
import katex from "katex";

export function PaperPreview() {
  const { status, editedSections, validation } = usePaperStore();

  // Extract content from result (from API response) or paper_content
  const result = status?.result ?? null;

  // Check if we have any content to display
  const paperSections = result ? {
    abstract: result.abstract || "",
    introduction: result.introduction || "",
    "related work": result.related_work || "",
    methodology: result.methodology || "",
    implementation: result.implementation || "",
    results: result.results || "",
    conclusion: result.conclusion || "",
  } : {};

  // Build display content — prefer edited versions
  const hasContent = Object.values(paperSections).some(v => v) || Object.keys(editedSections).length > 0;

  const ieeeReport = validation?.ieee_report ?? status?.ieee_report;
  const title = result?.topic || status?.message || "Research Paper";
  const keywords = result?.keywords || [];
  const equations = Array.isArray(result?.equations) ? result.equations : [];
  const diagrams = Array.isArray(result?.diagrams) ? result.diagrams : [];
  const tables = Array.isArray(result?.tables) ? result.tables : [];

  const renderEquation = (raw: string) => {
    if (!raw) return null;
    try {
      const html = katex.renderToString(raw, { throwOnError: false, displayMode: true });
      return <div className="overflow-x-auto" dangerouslySetInnerHTML={{ __html: html }} />;
    } catch {
      return <code className="text-xs">{raw}</code>;
    }
  };

  return (
    <Card className="h-full flex flex-col bg-[var(--card)] backdrop-filter-none">
      <CardHeader className="pb-2 shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <BookOpen className="h-4 w-4" /> IEEE Preview
          </CardTitle>
          {ieeeReport && (
            <Badge variant={ieeeReport.is_ieee_ready ? "success" : "warning"}>
              {ieeeReport.is_ieee_ready ? "IEEE Ready" : "Needs Review"}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 min-h-0">
        <ScrollArea className="h-full pr-3">
          {hasContent ? (
            <div className="paper-content space-y-4 pb-4">
              {/* Title & Keywords */}
              <div className="text-center border-b border-[var(--border)] pb-4">
                <h1 className="text-xl font-bold">
                  {title}
                </h1>
                {keywords && keywords.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1 justify-center">
                    {keywords.map((kw: string, i: number) => (
                      <Badge key={i} variant="outline" className="text-xs">
                        {kw}
                      </Badge>
                    ))}
                  </div>
                )}
                <p className="text-xs text-[var(--muted-foreground)] mt-2">
                  AI-Generated IEEE Format Paper
                </p>
              </div>

              {/* Display Sections in Order */}
              {IEEE_SECTIONS.map((section) => {
                if (section === "References") return null;

                // Map section display names to result property names
                const sectionMap: Record<string, string> = {
                  "Abstract": "abstract",
                  "Introduction": "introduction",
                  "Related Work": "related_work",
                  "Proposed Methodology": "methodology",
                  "Implementation & Results": "implementation",
                  "Results & Discussion": "results",
                  "Conclusion": "conclusion",
                };
                
                const resultKey = sectionMap[section];
                const apiContent = result && resultKey ? result[resultKey] : null;
                const editedContent = editedSections[section];
                const text = editedContent ?? apiContent ?? "";
                
                if (!text) return null;
                
                return (
                  <div key={section}>
                    <h2 className="text-base font-bold uppercase tracking-wide border-b border-[var(--border)] pb-1 mb-2">
                      {section}
                    </h2>
                    <div className="text-sm whitespace-pre-wrap leading-relaxed">
                      {text}
                    </div>
                  </div>
                );
              })}

              {/* References Section (if available) */}
              {result?.references && result.references.length > 0 && (
                <div>
                  <h2 className="text-base font-bold uppercase tracking-wide border-b border-[var(--border)] pb-1 mb-2">
                    References
                  </h2>
                  <div className="text-sm space-y-2">
                    {result.references.map((ref: Record<string, any>, i: number) => (
                      <div key={i} className="text-xs">
                        <p>
                          <span className="font-semibold">[{i + 1}]</span> {ref.title}
                        </p>
                        <p className="text-[var(--muted-foreground)]">
                          {ref.source || ref.url}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {equations.length > 0 && (
                <div>
                  <h2 className="text-base font-bold uppercase tracking-wide border-b border-[var(--border)] pb-1 mb-2">
                    Equations
                  </h2>
                  <div className="space-y-3">
                    {equations.map((eq: Record<string, any>, i: number) => (
                      <div key={i} className="rounded border border-[var(--border)] p-3">
                        <p className="text-xs text-[var(--muted-foreground)] mb-2">Equation ({i + 1})</p>
                        {renderEquation(eq.latex || eq.input || eq.notation || "")}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {tables.length > 0 && (
                <div>
                  <h2 className="text-base font-bold uppercase tracking-wide border-b border-[var(--border)] pb-1 mb-2">
                    Tables
                  </h2>
                  <div className="space-y-4">
                    {tables.map((tb: Record<string, any>, i: number) => (
                      <div key={i} className="rounded border border-[var(--border)] p-3">
                        <p className="text-sm font-medium">Table {i + 1}: {tb.caption || "Model Performance"}</p>
                        <div className="overflow-x-auto mt-2">
                          <table className="min-w-full text-xs border-collapse">
                            <thead>
                              <tr>
                                {(tb.headers || []).map((h: string, j: number) => (
                                  <th key={j} className="border px-2 py-1 bg-[var(--muted)] text-left">{h}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {(tb.rows || []).map((row: string[], rIdx: number) => (
                                <tr key={rIdx}>
                                  {row.map((cell: string, cIdx: number) => (
                                    <td key={cIdx} className="border px-2 py-1">{cell}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {diagrams.length > 0 && (
                <div>
                  <h2 className="text-base font-bold uppercase tracking-wide border-b border-[var(--border)] pb-1 mb-2">
                    Figures
                  </h2>
                  <div className="text-xs space-y-1">
                    {diagrams.map((dg: Record<string, any>, i: number) => (
                      <p key={i}>Fig. {i + 1}. {dg.caption || dg.label || "Diagram"}</p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-[var(--muted-foreground)]">
              <BookOpen className="h-10 w-10 mb-3 opacity-30" />
              <p className="text-sm">Paper preview will appear here</p>
              <p className="text-xs mt-1">Generate a paper to get started</p>
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
