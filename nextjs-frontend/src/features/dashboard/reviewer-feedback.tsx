"use client";

import {
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  Star,
} from "lucide-react";
import { usePaperStore } from "@/store/paper-store";
import type { NoveltyAnalysis } from "@/types";
import { formatScore, scoreColor } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";

const decisionConfig = {
  accept: { label: "Accept", variant: "success" as const, icon: ThumbsUp },
  minor_revision: { label: "Minor Revision", variant: "warning" as const, icon: AlertTriangle },
  major_revision: { label: "Major Revision", variant: "destructive" as const, icon: AlertTriangle },
  reject: { label: "Reject", variant: "destructive" as const, icon: ThumbsDown },
};

export function ReviewerFeedback() {
  const { validation, status } = usePaperStore();
  const enhancement = validation?.enhancement_scores ?? status?.enhancement_scores;
  const review = enhancement?.review_report;
  const novelty: NoveltyAnalysis | null | undefined = enhancement?.novelty_analysis;
  const quality = enhancement?.quality_report;
  const citation = enhancement?.citation_report;

  if (!review && !novelty) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center h-48 text-[var(--muted-foreground)]">
          <MessageSquare className="h-10 w-10 mb-3 opacity-30" />
          <p className="text-sm">Reviewer feedback appears after enhancement</p>
        </CardContent>
      </Card>
    );
  }

  const decision = review?.decision
    ? decisionConfig[review.decision]
    : null;
  const DecisionIcon = decision?.icon ?? Star;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <MessageSquare className="h-5 w-5" /> AI Reviewer
          </CardTitle>
          {decision && (
            <Badge variant={decision.variant}>
              <DecisionIcon className="h-3 w-3 mr-1" />
              {decision.label}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-3">
          <div className="space-y-5">
            {/* Overall score */}
            {review && (
              <div className="text-center">
                <span className={`text-3xl font-bold ${scoreColor(review.overall_score)}`}>
                  {formatScore(review.overall_score)}
                </span>
                <span className="text-sm text-[var(--muted-foreground)] ml-1">/100</span>
                <p className="text-xs text-[var(--muted-foreground)] mt-1">
                  {review.passes_completed} review pass{review.passes_completed !== 1 ? "es" : ""} completed
                </p>
              </div>
            )}

            {/* Dimensions */}
            {review?.dimensions && review.dimensions.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-semibold">Review Dimensions</h4>
                {review.dimensions.map((dim) => (
                  <div key={dim.name} className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{dim.name}</span>
                      <span className={`text-sm font-bold ${scoreColor(dim.score)}`}>
                        {formatScore(dim.score)}
                      </span>
                    </div>
                    <Progress value={dim.score} />
                    <p className="text-xs text-[var(--muted-foreground)]">{dim.feedback}</p>
                    {dim.suggestions.length > 0 && (
                      <ul className="text-xs space-y-0.5 pl-4 list-disc text-[var(--muted-foreground)]">
                        {dim.suggestions.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Reviewer comments */}
            {review?.reviewer_comments && (
              <>
                <Separator />
                <div>
                  <h4 className="text-sm font-semibold mb-2">Reviewer Comments</h4>
                  <p className="text-sm leading-relaxed text-[var(--muted-foreground)] whitespace-pre-wrap">
                    {review.reviewer_comments}
                  </p>
                </div>
              </>
            )}

            {/* Novelty analysis */}
            {novelty && (
              <>
                <Separator />
                <div>
                  <h4 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                    <Star className="h-3.5 w-3.5 text-[var(--novelty)]" /> Novelty Analysis
                  </h4>
                  {novelty?.problem_gap && (
                    <div className="mb-2">
                      <span className="text-xs font-medium text-[var(--muted-foreground)]">Problem Gap</span>
                      <p className="text-sm">{novelty.problem_gap}</p>
                    </div>
                  )}
                  {novelty?.proposed_innovation && (
                    <div className="mb-2">
                      <span className="text-xs font-medium text-[var(--muted-foreground)]">Innovation</span>
                      <p className="text-sm">{novelty.proposed_innovation}</p>
                    </div>
                  )}
                  {novelty?.technical_improvement && (
                    <div className="mb-2">
                      <span className="text-xs font-medium text-[var(--muted-foreground)]">Technical Improvement</span>
                      <p className="text-sm">{novelty.technical_improvement}</p>
                    </div>
                  )}
                  {novelty?.expected_impact && (
                    <div className="mb-2">
                      <span className="text-xs font-medium text-[var(--muted-foreground)]">Expected Impact</span>
                      <p className="text-sm">{novelty.expected_impact}</p>
                    </div>
                  )}
                  {(novelty?.novelty_score ?? null) !== null && (
                    <div className="mb-2">
                      <span className="text-xs font-medium text-[var(--muted-foreground)]">Novelty Score</span>
                      <p className="text-sm font-bold">{novelty!.novelty_score}/100</p>
                    </div>
                  )}
                </div>
              </>
            )}

            {/* Quality improvements */}
            {quality && (
              <>
                <Separator />
                <div>
                  <h4 className="text-sm font-semibold mb-2">Quality Improvements</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="bg-[var(--muted)] rounded-lg p-2 text-center">
                      <p className="font-bold text-[var(--quality)]">+{quality.total_words_added}</p>
                      <p className="text-[10px] text-[var(--muted-foreground)]">Words Added</p>
                    </div>
                    <div className="bg-[var(--muted)] rounded-lg p-2 text-center">
                      <p className="font-bold text-[var(--quality)]">{quality.repetition_fixes}</p>
                      <p className="text-[10px] text-[var(--muted-foreground)]">Repetitions Fixed</p>
                    </div>
                  </div>
                </div>
              </>
            )}

            {/* Citation report */}
            {citation && (
              <>
                <Separator />
                <div>
                  <h4 className="text-sm font-semibold mb-2">Citation Report</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="bg-[var(--muted)] rounded-lg p-2 text-center">
                      <p className="font-bold">{citation.total_citations_found}</p>
                      <p className="text-[10px] text-[var(--muted-foreground)]">Citations</p>
                    </div>
                    <div className="bg-[var(--muted)] rounded-lg p-2 text-center">
                      <p className="font-bold">{citation.total_references}</p>
                      <p className="text-[10px] text-[var(--muted-foreground)]">References</p>
                    </div>
                  </div>
                  <Badge
                    variant={citation.citation_reference_consistent ? "success" : "warning"}
                    className="mt-2"
                  >
                    {citation.citation_reference_consistent
                      ? "Citations Consistent"
                      : "Citation Issues Found"}
                  </Badge>
                </div>
              </>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
