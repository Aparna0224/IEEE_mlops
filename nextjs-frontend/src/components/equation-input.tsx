"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EquationInfo } from "@/types";

interface EquationInputProps {
  equations: EquationInfo[];
  onAdd: (equation: EquationInfo) => void;
  onRemove: (id: string) => void;
  onUpdate: (id: string, field: keyof EquationInfo, value: any) => void;
}

export function EquationInput({
  equations,
  onAdd,
  onRemove,
  onUpdate,
}: EquationInputProps) {
  const [isAdding, setIsAdding] = useState(false);
  const [newEquation, setNewEquation] = useState<Partial<EquationInfo>>({
    label: "",
    notation: "",
    description: "",
  });

  const handleAdd = () => {
    if (newEquation.label && newEquation.notation) {
      const equation: EquationInfo = {
        id: `eq-${Date.now()}`,
        label: newEquation.label as string,
        notation: newEquation.notation as string,
        description: newEquation.description as string,
        latex: convertToLatex(newEquation.notation as string),
      };
      onAdd(equation);
      setNewEquation({ label: "", notation: "", description: "" });
      setIsAdding(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Mathematical Equations</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {equations.length > 0 && (
          <div className="space-y-3">
            {equations.map((eq) => (
              <div
                key={eq.id}
                className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-900"
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                  <div>
                    <label className="text-sm font-medium">Label</label>
                    <Input
                      value={eq.label}
                      onChange={(e) =>
                        onUpdate(eq.id, "label", e.target.value)
                      }
                      placeholder="e.g., eq:average"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="text-sm font-medium">Notation</label>
                    <Input
                      value={eq.notation}
                      onChange={(e) =>
                        onUpdate(eq.id, "notation", e.target.value)
                      }
                      placeholder="e.g., 1/N * sum(x_i)"
                    />
                  </div>
                </div>
                {eq.description && (
                  <div className="mb-3">
                    <label className="text-sm font-medium">Description</label>
                    <Textarea
                      value={eq.description}
                      onChange={(e) =>
                        onUpdate(eq.id, "description", e.target.value)
                      }
                      placeholder="Optional description"
                      rows={2}
                    />
                  </div>
                )}
                {eq.latex && (
                  <div className="text-xs text-amber-600 dark:text-amber-400 mb-2">
                    LaTeX: {eq.latex}
                  </div>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onRemove(eq.id)}
                  className="text-red-500 hover:text-red-700"
                >
                  <Trash2 className="w-4 h-4 mr-2" /> Remove
                </Button>
              </div>
            ))}
          </div>
        )}

        {isAdding ? (
          <div className="border rounded-lg p-4 bg-blue-50 dark:bg-blue-900/20">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
              <div>
                <label className="text-sm font-medium">Label</label>
                <Input
                  value={newEquation.label as string}
                  onChange={(e) =>
                    setNewEquation((p) => ({
                      ...p,
                      label: e.target.value,
                    }))
                  }
                  placeholder="e.g., eq:entropy"
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-sm font-medium">Notation</label>
                <Input
                  value={newEquation.notation as string}
                  onChange={(e) =>
                    setNewEquation((p) => ({
                      ...p,
                      notation: e.target.value,
                    }))
                  }
                  placeholder="e.g., -sum(p_i * log(p_i))"
                />
              </div>
            </div>
            <div className="mb-3">
              <label className="text-sm font-medium">Description (Optional)</label>
              <Textarea
                value={newEquation.description as string}
                onChange={(e) =>
                  setNewEquation((p) => ({
                    ...p,
                    description: e.target.value,
                  }))
                }
                placeholder="Explain this equation"
                rows={2}
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={handleAdd} className="bg-blue-600">
                Add Equation
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setIsAdding(false);
                  setNewEquation({});
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <Button
            variant="outline"
            onClick={() => setIsAdding(true)}
            className="w-full"
          >
            <Plus className="w-4 h-4 mr-2" /> Add Equation
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function convertToLatex(notation: string): string {
  let latex = notation
    .replace(/sum\((.*?)\)/g, "\\sum $1")
    .replace(/sqrt\((.*?)\)/g, "\\sqrt{$1}")
    .replace(/(\d+)\/(\d+)/g, "\\frac{$1}{$2}")
    .replace(/\^(\d+)/g, "^{$1}")
    .replace(/_(\w+)/g, "_{$1}");
  return latex;
}
