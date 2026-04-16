"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ResearchPaperForm } from "@/components/research-paper-form";
import { TopicInput } from "@/features/paper/topic-input";
import { Lightbulb, BookOpen } from "lucide-react";

export default function ResearchPaperPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* ─ HEADER ─ */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-3 mb-4">
            <BookOpen className="w-10 h-10 text-blue-600" />
            <h1 className="text-4xl font-bold text-slate-900 dark:text-white">
              IEEE Research Paper Generator
            </h1>
          </div>
          <p className="text-lg text-slate-600 dark:text-slate-300">
            Generate IEEE-formatted conference papers from structured research data
          </p>
        </div>

        {/* ─ TABS: SIMPLE vs STRUCTURED ─ */}
        <Tabs defaultValue="structured" className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-8">
            <TabsTrigger value="structured" className="text-base">
              <BookOpen className="w-4 h-4 mr-2" />
              Structured Input
            </TabsTrigger>
            <TabsTrigger value="quick" className="text-base">
              <Lightbulb className="w-4 h-4 mr-2" />
              Quick Start
            </TabsTrigger>
          </TabsList>

          {/* ─ TAB 1: STRUCTURED RESEARCH INPUT ─ */}
          <TabsContent value="structured" className="space-y-6">
            <Card className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20">
              <CardHeader>
                <CardTitle>Comprehensive Research Paper Form</CardTitle>
                <CardDescription>
                  Fill in detailed research information to generate a complete IEEE-formatted paper.
                  All fields are organized for easy data entry.
                </CardDescription>
              </CardHeader>
            </Card>

            <ResearchPaperForm />
          </TabsContent>

          {/* ─ TAB 2: QUICK START ─ */}
          <TabsContent value="quick" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Quick Paper Generation</CardTitle>
                <CardDescription>
                  Enter a research topic and let AI handle the rest. For more control,
                  use the Structured Input tab above.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <TopicInput />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* ─ HELP SECTION ─ */}
        <Card className="mt-12 border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
          <CardHeader>
            <CardTitle className="text-base">💡 Tips for Best Results</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="font-semibold mb-2">Structured Tab:</h4>
              <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-300">
                <li>Provide detailed problem statement</li>
                <li>Include specific methodology details</li>
                <li>Add diagrams for visual clarity</li>
                <li>Include equations with explanations</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-2">Quick Start Tab:</h4>
              <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-300">
                <li>Use for rapid prototype generation</li>
                <li>Perfect for exploring ideas</li>
                <li>Edit generated content afterward</li>
                <li>Great for student researchers</li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* ─ FEATURES ─ */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-12">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">📊 Structured Inputs</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-slate-600 dark:text-slate-300">
              Organized forms for title, authors, keywords, problem statement, methodology, and more.
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">📈 Equations & Diagrams</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-slate-600 dark:text-slate-300">
              Add mathematical equations (auto-converted to LaTeX) and upload diagrams (PNG/JPG/SVG).
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">📄 IEEE Format</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-slate-600 dark:text-slate-300">
              Generates publication-ready IEEE conference papers in LaTeX with 2-column layout.
            </CardContent>
          </Card>
        </div>

        {/* ─ WORKFLOW INFO ─ */}
        <Card className="mt-12 bg-slate-50 dark:bg-slate-900/50">
          <CardHeader>
            <CardTitle>Paper Generation Workflow</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-sm">
              <div className="text-center flex-1">
                <div className="bg-blue-100 dark:bg-blue-900 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-2 font-bold">
                  1
                </div>
                <p className="font-medium">Input</p>
                <p className="text-xs text-slate-500">Your research data</p>
              </div>
              <div className="text-2xl text-slate-300 dark:text-slate-600">→</div>

              <div className="text-center flex-1">
                <div className="bg-green-100 dark:bg-green-900 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-2 font-bold">
                  2
                </div>
                <p className="font-medium">Research</p>
                <p className="text-xs text-slate-500">Fetch & analyze papers</p>
              </div>
              <div className="text-2xl text-slate-300 dark:text-slate-600">→</div>

              <div className="text-center flex-1">
                <div className="bg-purple-100 dark:bg-purple-900 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-2 font-bold">
                  3
                </div>
                <p className="font-medium">Write</p>
                <p className="text-xs text-slate-500">Generate sections</p>
              </div>
              <div className="text-2xl text-slate-300 dark:text-slate-600">→</div>

              <div className="text-center flex-1">
                <div className="bg-orange-100 dark:bg-orange-900 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-2 font-bold">
                  4
                </div>
                <p className="font-medium">Format</p>
                <p className="text-xs text-slate-500">IEEE LaTeX</p>
              </div>
              <div className="text-2xl text-slate-300 dark:text-slate-600">→</div>

              <div className="text-center flex-1">
                <div className="bg-red-100 dark:bg-red-900 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-2 font-bold">
                  5
                </div>
                <p className="font-medium">Review</p>
                <p className="text-xs text-slate-500">Quality check</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
