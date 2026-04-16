"use client";

import { useEffect, useRef } from "react";
import { usePaperStore } from "@/store/paper-store";
import { IEEE_SECTIONS } from "@/types";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText } from "lucide-react";

/**
 * Parse the generated paper content into sections by matching IEEE headings.
 */
export function parseSections(content: string): Record<string, string> {
  const sections: Record<string, string> = {};
  let currentSection = "Abstract";
  const lines = content.split("\n");
  const sectionBuf: string[] = [];

  for (const line of lines) {
    const heading = IEEE_SECTIONS.find(
      (s) =>
        line.trim().toLowerCase().startsWith(s.toLowerCase()) ||
        line.trim().toLowerCase().replace(/^#+\s*/, "").startsWith(s.toLowerCase()) ||
        line.trim().toLowerCase().replace(/^\d+\.\s*/, "").startsWith(s.toLowerCase())
    );
    if (heading && sectionBuf.length > 0) {
      sections[currentSection] = sectionBuf.join("\n").trim();
      sectionBuf.length = 0;
      currentSection = heading;
    } else {
      sectionBuf.push(line);
    }
  }
  if (sectionBuf.length > 0) {
    sections[currentSection] = sectionBuf.join("\n").trim();
  }

  return sections;
}

export function SectionEditor() {
  const { status, editedSections, setEditedSection } = usePaperStore();
  const populated = useRef(false);

  // Extract content from result fields (current API) or legacy paper_content
  const result = status?.result as Record<string, any> | undefined;
  const rawContent = status?.paper_content ?? null;

  const sectionsFromResult: Record<string, string> = {
    Abstract: result?.abstract ?? "",
    Introduction: result?.introduction ?? "",
    "Related Work": result?.related_work ?? "",
    "Proposed Methodology": result?.methodology ?? "",
    "Implementation & Results": result?.implementation ?? "",
    "Results & Discussion": result?.results ?? "",
    Conclusion: result?.conclusion ?? "",
  };

  const sectionsFromRaw = rawContent ? parseSections(rawContent) : {};
  const sections = Object.values(sectionsFromResult).some(Boolean)
    ? sectionsFromResult
    : sectionsFromRaw;

  // Auto-populate editedSections once from best available source
  useEffect(() => {
    if (
      (Object.values(sections).some(Boolean) || rawContent) &&
      !populated.current &&
      Object.keys(editedSections).length === 0
    ) {
      Object.entries(sections).forEach(([name, text]) => {
        if (!text) return;
        setEditedSection(name, text);
      });
      populated.current = true;
    }
  }, [rawContent, sections, editedSections, setEditedSection]);

  // Merge: edited overrides parsed
  const allSections = { ...sections, ...editedSections };
  const sectionNames = Object.keys(allSections).length > 0
    ? Object.keys(allSections)
    : [...IEEE_SECTIONS];

  return (
    <Card className="h-full flex flex-col bg-[var(--card)] backdrop-filter-none">
      <CardHeader className="pb-2 shrink-0">
        <CardTitle className="text-base flex items-center gap-2">
          <FileText className="h-4 w-4" /> Section Editor
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0">
        <ScrollArea className="h-full pr-3">
          <div className="space-y-5 pb-4">
            {sectionNames.map((name) => (
              <div key={name} className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium">{name}</label>
                  {editedSections[name] !== undefined && (
                    <Badge variant="outline" className="text-[10px] h-4">
                      Edited
                    </Badge>
                  )}
                </div>
                <Textarea
                  className="min-h-[120px] text-sm font-mono leading-relaxed"
                  placeholder={`${name} content will appear here…`}
                  value={allSections[name] ?? ""}
                  onChange={(e) => setEditedSection(name, e.target.value)}
                />
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
