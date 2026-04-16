"use client";

import {
  BarChart3,
  ShieldCheck,
  Sparkles,
  BookCheck,
  MessageSquareWarning,
  TrendingUp,
} from "lucide-react";
import {
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
  PolarAngleAxis,
} from "recharts";
import { usePaperStore } from "@/store/paper-store";
import { formatScore, scoreColor, scoreBg } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

function ScoreRing({
  score,
  color,
  label,
}: {
  score: number;
  color: string;
  label: string;
}) {
  const data = [{ value: score, fill: color }];
  return (
    <div className="flex flex-col items-center">
      <div className="w-20 h-20">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            innerRadius="70%"
            outerRadius="100%"
            data={data}
            startAngle={90}
            endAngle={-270}
          >
            <PolarAngleAxis
              type="number"
              domain={[0, 100]}
              tick={false}
              angleAxisId={0}
            />
            <RadialBar
              background={{ fill: "var(--muted)" }}
              dataKey="value"
              angleAxisId={0}
              cornerRadius={10}
            />
          </RadialBarChart>
        </ResponsiveContainer>
      </div>
      <span className="text-lg font-bold mt-1" style={{ color }}>
        {formatScore(score)}
      </span>
      <span className="text-xs text-[var(--muted-foreground)]">{label}</span>
    </div>
  );
}

function MetricRow({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number | boolean;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex items-center justify-between py-1.5 text-sm">
      <span className="flex items-center gap-2 text-[var(--muted-foreground)]">
        {Icon && <Icon className="h-3.5 w-3.5" />}
        {label}
      </span>
      <span className="font-medium">
        {typeof value === "boolean" ? (
          <Badge variant={value ? "success" : "warning"} className="text-[10px]">
            {value ? "Yes" : "No"}
          </Badge>
        ) : (
          value
        )}
      </span>
    </div>
  );
}

export function QualityMetrics() {
  const { validation, status } = usePaperStore();

  const vr = validation ?? status?.validation_result;
  const enhancement = validation?.enhancement_scores ?? status?.enhancement_scores;
  const ieeeReport = validation?.ieee_report ?? status?.ieee_report;

  if (!vr && !enhancement) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center h-48 text-[var(--muted-foreground)]">
          <BarChart3 className="h-10 w-10 mb-3 opacity-30" />
          <p className="text-sm">Quality metrics appear after generation</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <BarChart3 className="h-5 w-5" /> Quality Metrics
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Score rings */}
        <div className="flex justify-around">
          {vr && (
            <ScoreRing
              score={vr.overall_quality_score}
              color="var(--quality)"
              label="Quality"
            />
          )}
          {enhancement && (
            <>
              <ScoreRing
                score={enhancement.novelty_score}
                color="var(--novelty)"
                label="Novelty"
              />
              <ScoreRing
                score={enhancement.ieee_compliance_score}
                color="var(--ieee)"
                label="IEEE"
              />
              <ScoreRing
                score={enhancement.reviewer_score}
                color="var(--reviewer)"
                label="Review"
              />
            </>
          )}
        </div>

        <Separator />

        {/* Content metrics */}
        {vr && (
          <div>
            <h4 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
              <BookCheck className="h-3.5 w-3.5" /> Content
            </h4>
            <MetricRow label="Words" value={vr.content_metrics.word_count} />
            <MetricRow label="Sentences" value={vr.content_metrics.sentence_count} />
            <MetricRow
              label="Vocabulary Richness"
              value={`${(vr.content_metrics.vocabulary_richness * 100).toFixed(0)}%`}
            />
            <MetricRow
              label="Flesch-Kincaid Grade"
              value={vr.content_metrics.flesch_kincaid_grade.toFixed(1)}
            />
          </div>
        )}

        {/* Structure metrics */}
        {vr && (
          <div>
            <h4 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5" /> Structure
            </h4>
            <MetricRow label="Sections" value={vr.structure_metrics.section_count} />
            <MetricRow label="Has Introduction" value={vr.structure_metrics.has_introduction} />
            <MetricRow label="Has Conclusion" value={vr.structure_metrics.has_conclusion} />
            <MetricRow label="Has Citations" value={vr.structure_metrics.has_citations} />
          </div>
        )}

        {/* Enhancement stats */}
        {enhancement && (
          <div>
            <h4 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5" /> Enhancement
            </h4>
            <MetricRow label="Total Actions" value={enhancement.total_actions} />
            <MetricRow
              label="Time"
              value={`${enhancement.enhancement_time_seconds.toFixed(1)}s`}
            />
            <MetricRow
              label="Stages"
              value={enhancement.stages_completed.length}
            />
          </div>
        )}

        {/* IEEE report */}
        {ieeeReport && (
          <div>
            <h4 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5" /> IEEE Compliance
            </h4>
            <MetricRow label="IEEE Ready" value={ieeeReport.is_ieee_ready} />
            <MetricRow label="References" value={ieeeReport.reference_count} />
            <MetricRow label="Duplicates Removed" value={ieeeReport.duplicates_removed} />
            <MetricRow
              label="Citation Consistency"
              value={ieeeReport.citation_reference_consistent}
            />
          </div>
        )}

        {/* Warnings */}
        {vr && vr.validation_warnings.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2 flex items-center gap-1.5 text-amber-500">
              <MessageSquareWarning className="h-3.5 w-3.5" /> Warnings
            </h4>
            <ul className="space-y-1">
              {vr.validation_warnings.map((w, i) => (
                <li
                  key={i}
                  className="text-xs text-amber-600 dark:text-amber-400 bg-amber-500/5 rounded px-2 py-1"
                >
                  {w}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
