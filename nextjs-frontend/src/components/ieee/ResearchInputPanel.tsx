/**
 * Research Input Panel
 * ───────────────────
 * Complete interface for providing research topic, diagrams,
 * equations, and additional notes for IEEE paper generation.
 */

'use client'

import React, { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DiagramUploader, DiagramData } from './DiagramUploader'
import { EquationEditor, EquationData } from './EquationEditor'
import { Settings2 } from 'lucide-react'

export interface ResearchInputData {
  topic: string
  diagrams: DiagramData[]
  equations: EquationData[]
  notes: string
  authors: Array<{
    name: string
    affiliation: string
    email?: string
  }>
  maxReferences: number
  model: string
}

interface ResearchInputPanelProps {
  onGenerate: (data: ResearchInputData) => void
  isLoading?: boolean
}

export function ResearchInputPanel({ onGenerate, isLoading = false }: ResearchInputPanelProps) {
  const [topic, setTopic] = useState('')
  const [diagrams, setDiagrams] = useState<DiagramData[]>([])
  const [equations, setEquations] = useState<EquationData[]>([])
  const [notes, setNotes] = useState('')
  const [authors, setAuthors] = useState([
    { name: '', affiliation: '', email: '' },
  ])
  const [maxReferences, setMaxReferences] = useState(5)
  const [model, setModel] = useState('openai/gpt-4o-mini')
  const [activeTab, setActiveTab] = useState('basic')

  const handleAddAuthor = () => {
    setAuthors([...authors, { name: '', affiliation: '', email: '' }])
  }

  const handleRemoveAuthor = (index: number) => {
    setAuthors(authors.filter((_, i) => i !== index))
  }

  const handleAuthorChange = (index: number, field: string, value: string) => {
    const updated = [...authors]
    updated[index] = { ...updated[index], [field]: value }
    setAuthors(updated)
  }

  const handleGenerate = () => {
    if (!topic.trim()) {
      alert('Please enter a research topic')
      return
    }

    onGenerate({
      topic,
      diagrams,
      equations,
      notes,
      authors: authors.filter(a => a.name.trim()),
      maxReferences,
      model,
    })
  }

  const hasContent = topic.trim().length > 0
  const totalAssets = diagrams.length + equations.length

  return (
    <div className="space-y-4">
      <Card className="p-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="basic">Topic & Notes</TabsTrigger>
            <TabsTrigger value="diagrams">
              Diagrams
              {diagrams.length > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {diagrams.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="equations">
              Equations
              {equations.length > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {equations.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          {/* Basic Tab */}
          <TabsContent value="basic" className="space-y-4 mt-4">
            <div>
              <label className="text-sm font-medium mb-2 block">
                Research Topic *
              </label>
              <Input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g., Zero Trust Threat Detection Architecture"
                className="text-base"
              />
              <p className="text-xs text-gray-500 mt-1">
                This will be used as the paper title and for reference discovery
              </p>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">
                Additional Notes & Context
              </label>
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add any additional context, requirements, or specific aspects you want to emphasize in the paper..."
                rows={6}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Authors</label>
              <div className="space-y-3">
                {authors.map((author, index) => (
                  <div key={index} className="grid grid-cols-12 gap-2">
                    <Input
                      value={author.name}
                      onChange={(e) =>
                        handleAuthorChange(index, 'name', e.target.value)
                      }
                      placeholder="Full name"
                      className="col-span-4 text-sm"
                    />
                    <Input
                      value={author.affiliation}
                      onChange={(e) =>
                        handleAuthorChange(index, 'affiliation', e.target.value)
                      }
                      placeholder="Institution"
                      className="col-span-5 text-sm"
                    />
                    <Input
                      value={author.email || ''}
                      onChange={(e) =>
                        handleAuthorChange(index, 'email', e.target.value)
                      }
                      placeholder="email@edu"
                      className="col-span-2 text-sm"
                    />
                    {authors.length > 1 && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleRemoveAuthor(index)}
                        className="col-span-1"
                      >
                        ✕
                      </Button>
                    )}
                  </div>
                ))}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleAddAuthor}
                className="mt-2"
              >
                + Add Author
              </Button>
            </div>
          </TabsContent>

          {/* Diagrams Tab */}
          <TabsContent value="diagrams" className="mt-4">
            <DiagramUploader
              onDiagramsChange={setDiagrams}
              maxDiagrams={5}
            />
          </TabsContent>

          {/* Equations Tab */}
          <TabsContent value="equations" className="mt-4">
            <EquationEditor
              onEquationsChange={setEquations}
              maxEquations={10}
            />
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings" className="space-y-4 mt-4">
            <div>
              <label className="text-sm font-medium mb-2 block">
                LLM Model
              </label>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger>
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="openai/gpt-4o-mini">
                    GPT-4o Mini (Fast & Cheap)
                  </SelectItem>
                  <SelectItem value="openai/gpt-4-turbo">
                    GPT-4 Turbo (Better Quality)
                  </SelectItem>
                  <SelectItem value="anthropic/claude-3-haiku">
                    Claude 3 Haiku (Fast)
                  </SelectItem>
                  <SelectItem value="anthropic/claude-3-sonnet">
                    Claude 3 Sonnet (Balanced)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">
                Max References to Fetch
              </label>
              <Select value={String(maxReferences)} onValueChange={(v) => setMaxReferences(Number(v))}>
                <SelectTrigger>
                  <SelectValue placeholder="Select max references" />
                </SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 5, 7, 10].map((n) => (
                    <SelectItem key={n} value={String(n)}>
                      {n} papers
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-500 mt-1">
                More references = more comprehensive but slower generation
              </p>
            </div>

            <Card className="p-3 bg-blue-50 border-blue-200">
              <div className="flex gap-2">
                <Settings2 className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="text-xs text-blue-900">
                  <p className="font-medium">Paper Generation Summary</p>
                  <p className="mt-1">
                    • Topic: <strong>{topic || 'Not set'}</strong>
                    <br />• Diagrams: <strong>{diagrams.length}</strong>
                    <br />• Equations: <strong>{equations.length}</strong>
                    <br />• Authors: <strong>{authors.filter(a => a.name.trim()).length}</strong>
                  </p>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Action Buttons */}
        <div className="flex gap-2 mt-6 pt-4 border-t">
          <Button
            onClick={handleGenerate}
            disabled={!hasContent || isLoading}
            size="lg"
            className="flex-1"
          >
            {isLoading ? 'Generating...' : 'Generate IEEE Paper'}
          </Button>
          {totalAssets > 0 && (
            <Badge variant="outline" className="px-3 py-2">
              {totalAssets} assets
            </Badge>
          )}
        </div>
      </Card>
    </div>
  )
}
