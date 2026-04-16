"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EquationInput } from "./equation-input";
import { DiagramUploader } from "./diagram-uploader";
import { useMutation } from "@tanstack/react-query";
import { generatePaper } from "@/services/api";
import { usePaperStore } from "@/store/paper-store";
import type { ResearchStructure, EquationInfo, DiagramInfo, AuthorInfo } from "@/types";
import { Sparkles, Plus, Trash2 } from "lucide-react";

export function ResearchPaperForm() {
  const { setTaskId, setCurrentStage } = usePaperStore();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [keywordInput, setKeywordInput] = useState("");
  const [authorInput, setAuthorInput] = useState("");

  const [formData, setFormData] = useState<ResearchStructure>({
    title: "",
    authors: [{ name: "", affiliation: "", location: "", email: "" }],
    keywords: [],
    research_topic: "",
    problem_statement: "",
    proposed_solution: "",
    objective: "",
    methodology: "",
    dataset: "",
    experiments: "",
    equations: [],
    diagrams: [],
    notes: "",
  });

  const mutation = useMutation({
    mutationFn: generatePaper,
    onSuccess: (data) => {
      setTaskId(data.task_id);
      setCurrentStage("research");
      setIsSubmitting(false);
    },
    onError: (error) => {
      console.error("Generation failed:", error);
      setIsSubmitting(false);
    },
  });

  const handleInputChange = (
    field: keyof ResearchStructure,
    value: any
  ) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleAuthorChange = (
    index: number,
    field: keyof AuthorInfo,
    value: string
  ) => {
    setFormData((prev) => ({
      ...prev,
      authors: prev.authors.map((a, i) =>
        i === index ? { ...a, [field]: value } : a
      ),
    }));
  };

  const addAuthor = () => {
    if (formData.authors.length < 6) {
      setFormData((prev) => ({
        ...prev,
        authors: [
          ...prev.authors,
          { name: "", affiliation: "", location: "", email: "" },
        ],
      }));
    }
  };

  const removeAuthor = (index: number) => {
    if (formData.authors.length > 1) {
      setFormData((prev) => ({
        ...prev,
        authors: prev.authors.filter((_, i) => i !== index),
      }));
    }
  };

  const addKeyword = () => {
    if (
      keywordInput.trim() &&
      formData.keywords.length < 6 &&
      !formData.keywords.includes(keywordInput.trim())
    ) {
      setFormData((prev) => ({
        ...prev,
        keywords: [...prev.keywords, keywordInput.trim()],
      }));
      setKeywordInput("");
    }
  };

  const removeKeyword = (keyword: string) => {
    setFormData((prev) => ({
      ...prev,
      keywords: prev.keywords.filter((k) => k !== keyword),
    }));
  };

  const handleEquationAdd = (eq: EquationInfo) => {
    setFormData((prev) => ({
      ...prev,
      equations: [...prev.equations, eq],
    }));
  };

  const handleEquationRemove = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      equations: prev.equations.filter((e) => e.id !== id),
    }));
  };

  const handleEquationUpdate = (
    id: string,
    field: keyof EquationInfo,
    value: any
  ) => {
    setFormData((prev) => ({
      ...prev,
      equations: prev.equations.map((e) =>
        e.id === id ? { ...e, [field]: value } : e
      ),
    }));
  };

  const handleDiagramAdd = (diagram: DiagramInfo) => {
    setFormData((prev) => ({
      ...prev,
      diagrams: [...prev.diagrams, diagram],
    }));
  };

  const handleDiagramRemove = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      diagrams: prev.diagrams.filter((d) => d.id !== id),
    }));
  };

  const handleDiagramUpdate = (
    id: string,
    field: keyof DiagramInfo,
    value: any
  ) => {
    setFormData((prev) => ({
      ...prev,
      diagrams: prev.diagrams.map((d) =>
        d.id === id ? { ...d, [field]: value } : d
      ),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim() || !formData.research_topic.trim()) {
      alert("Please fill in title and research topic");
      return;
    }

    if (formData.authors.some((a) => !a.name.trim())) {
      alert("Please fill in all author names");
      return;
    }

    setIsSubmitting(true);
    mutation.mutate({
      topic: formData.research_topic,
      max_references: 5,
      model_name: "openai/gpt-4o-mini",
      authors: formData.authors,
      diagrams: formData.diagrams,
      equations: formData.equations,
      research_structure: formData,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <Tabs defaultValue="basic" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="basic">Basic Info</TabsTrigger>
          <TabsTrigger value="research">Research</TabsTrigger>
          <TabsTrigger value="technical">Technical</TabsTrigger>
          <TabsTrigger value="media">Media</TabsTrigger>
        </TabsList>

        {/* ─ TAB 1: BASIC INFO ─ */}
        <TabsContent value="basic" className="space-y-6 mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Paper Title & Keywords</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Paper Title *</label>
                <Input
                  value={formData.title}
                  onChange={(e) =>
                    handleInputChange("title", e.target.value)
                  }
                  placeholder="Enter your paper title"
                  className="mt-2"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Keywords (3-6)</label>
                <div className="mt-2">
                  <div className="flex gap-2 mb-3">
                    <Input
                      value={keywordInput}
                      onChange={(e) => setKeywordInput(e.target.value)}
                      placeholder="Type a keyword and press Add"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          addKeyword();
                        }
                      }}
                    />
                    <Button
                      type="button"
                      onClick={addKeyword}
                      variant="outline"
                    >
                      Add
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {formData.keywords.map((kw) => (
                      <Badge key={kw} variant="secondary">
                        {kw}
                        <button
                          type="button"
                          onClick={() => removeKeyword(kw)}
                          className="ml-2 text-red-500 hover:text-red-700"
                        >
                          ✕
                        </button>
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Authors</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {formData.authors.map((author, idx) => (
                <div
                  key={idx}
                  className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-900"
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                    <div>
                      <label className="text-sm font-medium">Name *</label>
                      <Input
                        value={author.name}
                        onChange={(e) =>
                          handleAuthorChange(idx, "name", e.target.value)
                        }
                        placeholder="Full name"
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Email</label>
                      <Input
                        type="email"
                        value={author.email}
                        onChange={(e) =>
                          handleAuthorChange(idx, "email", e.target.value)
                        }
                        placeholder="email@example.com"
                        className="mt-1"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="text-sm font-medium">Affiliation</label>
                      <Input
                        value={author.affiliation}
                        onChange={(e) =>
                          handleAuthorChange(
                            idx,
                            "affiliation",
                            e.target.value
                          )
                        }
                        placeholder="University/Institution"
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Location</label>
                      <Input
                        value={author.location}
                        onChange={(e) =>
                          handleAuthorChange(idx, "location", e.target.value)
                        }
                        placeholder="City, Country"
                        className="mt-1"
                      />
                    </div>
                  </div>
                  {formData.authors.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeAuthor(idx)}
                      className="mt-3 text-red-500"
                    >
                      <Trash2 className="w-4 h-4 mr-2" /> Remove
                    </Button>
                  )}
                </div>
              ))}

              {formData.authors.length < 6 && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={addAuthor}
                  className="w-full"
                >
                  <Plus className="w-4 h-4 mr-2" /> Add Author
                </Button>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─ TAB 2: RESEARCH ─ */}
        <TabsContent value="research" className="space-y-6 mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Research Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Research Topic *</label>
                <Input
                  value={formData.research_topic}
                  onChange={(e) =>
                    handleInputChange("research_topic", e.target.value)
                  }
                  placeholder="e.g., Federated Learning for Edge Computing"
                  className="mt-2"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Problem Statement</label>
                <Textarea
                  value={formData.problem_statement}
                  onChange={(e) =>
                    handleInputChange(
                      "problem_statement",
                      e.target.value
                    )
                  }
                  placeholder="Describe the problem you're addressing"
                  rows={3}
                  className="mt-2"
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  Proposed Solution / Research Idea
                </label>
                <Textarea
                  value={formData.proposed_solution}
                  onChange={(e) =>
                    handleInputChange(
                      "proposed_solution",
                      e.target.value
                    )
                  }
                  placeholder="Explain your proposed solution or research approach"
                  rows={3}
                  className="mt-2"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Research Objective</label>
                <Textarea
                  value={formData.objective}
                  onChange={(e) =>
                    handleInputChange("objective", e.target.value)
                  }
                  placeholder="What are you trying to achieve?"
                  rows={2}
                  className="mt-2"
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  Methodology / Technical Details
                </label>
                <Textarea
                  value={formData.methodology}
                  onChange={(e) =>
                    handleInputChange("methodology", e.target.value)
                  }
                  placeholder="Describe your research methodology"
                  rows={3}
                  className="mt-2"
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  Additional Notes
                </label>
                <Textarea
                  value={formData.notes}
                  onChange={(e) =>
                    handleInputChange("notes", e.target.value)
                  }
                  placeholder="Any additional information or context"
                  rows={2}
                  className="mt-2"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─ TAB 3: TECHNICAL ─ */}
        <TabsContent value="technical" className="space-y-6 mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Experimental Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Dataset Information</label>
                <Textarea
                  value={formData.dataset}
                  onChange={(e) =>
                    handleInputChange("dataset", e.target.value)
                  }
                  placeholder="Describe the datasets used (source, size, characteristics)"
                  rows={3}
                  className="mt-2"
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  Experimental Setup
                </label>
                <Textarea
                  value={formData.experiments}
                  onChange={(e) =>
                    handleInputChange("experiments", e.target.value)
                  }
                  placeholder="Details about your experiments (hardware, parameters, baselines)"
                  rows={3}
                  className="mt-2"
                />
              </div>
            </CardContent>
          </Card>

          <EquationInput
            equations={formData.equations}
            onAdd={handleEquationAdd}
            onRemove={handleEquationRemove}
            onUpdate={handleEquationUpdate}
          />
        </TabsContent>

        {/* ─ TAB 4: MEDIA ─ */}
        <TabsContent value="media" className="space-y-6 mt-6">
          <DiagramUploader
            diagrams={formData.diagrams}
            onAdd={handleDiagramAdd}
            onRemove={handleDiagramRemove}
            onUpdate={handleDiagramUpdate}
          />
        </TabsContent>
      </Tabs>

      {/* ─ SUBMIT BUTTON ─ */}
      <div className="mt-8 flex gap-3">
        <Button
          type="submit"
          disabled={isSubmitting || mutation.isPending}
          size="lg"
          className="bg-blue-600 hover:bg-blue-700"
        >
          <Sparkles className="w-4 h-4 mr-2" />
          {isSubmitting || mutation.isPending ? "Generating..." : "Generate IEEE Paper"}
        </Button>
        <Button type="button" variant="outline" size="lg">
          Save Draft
        </Button>
      </div>

      {mutation.isError && (
        <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-300">
          <p className="text-red-700 dark:text-red-400">
            Error: {mutation.error?.message || "Failed to generate paper"}
          </p>
        </div>
      )}
    </form>
  );
}
