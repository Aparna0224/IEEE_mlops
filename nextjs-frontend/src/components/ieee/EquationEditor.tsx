/**
 * Equation Editor Component
 * ─────────────────────────
 * Handles mathematical equation input with LaTeX/simple notation support.
 * Provides real-time LaTeX preview using KaTeX.
 */

'use client'

import React, { useState } from 'react'
import katex from 'katex'
import { Plus, X, ChevronDown } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

// Simple LaTeX renderer using inline style
const EquationPreview = ({ equation }: { equation: string }) => {
  let rendered = ''
  try {
    rendered = katex.renderToString(equation || '', { throwOnError: false, displayMode: true })
  } catch {
    rendered = ''
  }

  return (
    <div className="bg-gray-50 p-2 rounded border text-sm overflow-x-auto">
      {rendered ? (
        <div dangerouslySetInnerHTML={{ __html: rendered }} />
      ) : (
        <code className="font-mono">{equation}</code>
      )}
    </div>
  )
}

export interface EquationData {
  input: string
  label: string
  explanation: string
}

interface EquationEditorProps {
  onEquationsChange: (equations: EquationData[]) => void
  maxEquations?: number
}

export function EquationEditor({ onEquationsChange, maxEquations = 10 }: EquationEditorProps) {
  const [equations, setEquations] = useState<EquationData[]>([])
  const [newEquation, setNewEquation] = useState('')
  const [newLabel, setNewLabel] = useState('')
  const [newExplanation, setNewExplanation] = useState('')
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null)
  const [showForm, setShowForm] = useState(false)

  const addEquation = () => {
    if (!newEquation.trim()) return

    const equation: EquationData = {
      input: newEquation,
      label: newLabel.trim() || `eq_${equations.length + 1}`,
      explanation: newExplanation.trim(),
    }

    const updated = [...equations, equation]
    setEquations(updated)
    onEquationsChange(updated)

    // Reset form
    setNewEquation('')
    setNewLabel('')
    setNewExplanation('')
    setShowForm(false)
  }

  const removeEquation = (index: number) => {
    const updated = equations.filter((_, i) => i !== index)
    setEquations(updated)
    onEquationsChange(updated)
  }

  const updateEquation = (index: number, field: keyof EquationData, value: string) => {
    const updated = [...equations]
    updated[index][field] = value
    setEquations(updated)
    onEquationsChange(updated)
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold mb-2">Mathematical Equations</h3>
        <p className="text-xs text-gray-500 mb-3">
          Enter equations in simple notation or LaTeX format
        </p>

        {/* Equation List */}
        <div className="space-y-2">
          {equations.map((eq, index) => (
            <Card key={index} className="p-3">
              <div
                className="flex items-start justify-between cursor-pointer"
                onClick={() =>
                  setExpandedIndex(expandedIndex === index ? null : index)
                }
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="flex-shrink-0">
                      {eq.label}
                    </Badge>
                    <code className="text-xs font-mono text-gray-600 truncate">
                      {eq.input}
                    </code>
                  </div>
                  {eq.explanation && (
                    <p className="text-xs text-gray-500 mt-1 line-clamp-1">
                      {eq.explanation}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <ChevronDown
                    className={`h-4 w-4 transition-transform ${
                      expandedIndex === index ? 'rotate-180' : ''
                    }`}
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation()
                      removeEquation(index)
                    }}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </div>

              {expandedIndex === index && (
                <div className="mt-3 space-y-3 border-t pt-3">
                  <div>
                    <label className="text-xs font-medium">Equation Input</label>
                    <Input
                      value={eq.input}
                      onChange={(e) =>
                        updateEquation(index, 'input', e.target.value)
                      }
                      placeholder="S_i = (1/N) * sum(w_j * s_j)"
                      className="text-sm"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Supports: simple math, subscripts (x_i), fractions (a/b), functions (sum, sqrt)
                    </p>
                  </div>

                  <div>
                    <label className="text-xs font-medium">LaTeX Label</label>
                    <Input
                      value={eq.label}
                      onChange={(e) =>
                        updateEquation(index, 'label', e.target.value)
                      }
                      placeholder="eq:sentiment"
                      className="text-sm"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium">Explanation</label>
                    <Textarea
                      value={eq.explanation}
                      onChange={(e) =>
                        updateEquation(index, 'explanation', e.target.value)
                      }
                      placeholder="Explain what this equation represents..."
                      rows={2}
                      className="text-sm"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium">Preview</label>
                    <EquationPreview equation={eq.input} />
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>

        {/* Add Equation Form */}
        {!showForm ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowForm(true)}
            disabled={equations.length >= maxEquations}
            className="w-full mt-3"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Equation
          </Button>
        ) : (
          <Card className="p-4 mt-3">
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium">Equation Input</label>
                <Input
                  value={newEquation}
                  onChange={(e) => setNewEquation(e.target.value)}
                  placeholder="S_i = (1/N) * sum(w_j * s_j)"
                  autoFocus
                />
                <p className="text-xs text-gray-500 mt-1">
                  Examples: 1/N, sum(x_i), sqrt(x), x_i, S_compound
                </p>
              </div>

              <div>
                <label className="text-sm font-medium">LaTeX Label (optional)</label>
                <Input
                  value={newLabel}
                  onChange={(e) => setNewLabel(e.target.value)}
                  placeholder="eq:name"
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  Explanation (optional)
                </label>
                <Textarea
                  value={newExplanation}
                  onChange={(e) => setNewExplanation(e.target.value)}
                  placeholder="Explain this calculation..."
                  rows={2}
                />
              </div>

              <div>
                <label className="text-sm font-medium">Preview</label>
                <EquationPreview equation={newEquation} />
              </div>

              <div className="flex gap-2">
                <Button size="sm" onClick={addEquation}>
                  Add
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </Card>
        )}

        <p className="text-xs text-gray-500 mt-3">
          {equations.length} of {maxEquations} equations added
        </p>
      </div>
    </div>
  )
}
