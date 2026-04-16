/**
 * IEEE Paper Preview Component
 * ────────────────────────────
 * Displays generated paper information, diagrams, equations,
 * and references with download options.
 */

'use client'

import React, { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { AlertCircle, Download, FileText, Image, Sigma, BookOpen, CheckCircle } from 'lucide-react'

interface Diagram {
  diagram_id: string
  filename: string
  caption: string
  label: string
  width: number
}

interface Equation {
  equation_id: string
  original_input: string
  latex_equation: string
  label: string
  equation_number: number
  explanation: string
  variables: Record<string, string>
}

interface References {
  total_figures?: number
  total_equations?: number
  total_citations?: number
  total_references?: number
  [key: string]: any
}

interface IEEEPaperPreviewProps {
  taskId?: string
  pdfPath?: string
  latexSource?: string
  content?: string
  diagrams?: Diagram[]
  equations?: Equation[]
  references?: References
  keywords?: string[]
  isGenerated?: boolean
  isLoading?: boolean
  error?: string
}

export function IEEEPaperPreview({
  taskId = '',
  pdfPath = '',
  latexSource = '',
  content = '',
  diagrams = [],
  equations = [],
  references = {},
  keywords = [],
  isGenerated = false,
  isLoading = false,
  error = '',
}: IEEEPaperPreviewProps) {
  const [activeTab, setActiveTab] = useState('overview')

  const handleDownloadPDF = () => {
    if (pdfPath) {
      window.location.href = `/api/ieee/download/${taskId}`
    }
  }

  const handleDownloadLaTeX = () => {
    if (latexSource) {
      window.location.href = `/api/ieee/latex/${taskId}`
    }
  }

  const handleCopyContent = () => {
    if (content) {
      navigator.clipboard.writeText(content)
    }
  }

  if (isLoading) {
    return (
      <Card className="p-8 text-center">
        <div className="flex justify-center mb-4">
          <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
        </div>
        <p className="text-lg font-medium">Generating your IEEE paper...</p>
        <p className="text-sm text-gray-500 mt-2">This may take a few minutes</p>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-6 border-red-200 bg-red-50">
        <div className="flex gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-red-900">Generation Failed</h3>
            <p className="text-sm text-red-800 mt-1">{error}</p>
          </div>
        </div>
      </Card>
    )
  }

  if (!isGenerated) {
    return (
      <Card className="p-8 text-center">
        <BookOpen className="h-12 w-12 text-gray-300 mx-auto mb-4" />
        <p className="text-lg font-medium text-gray-500">No paper generated yet</p>
        <p className="text-sm text-gray-400 mt-2">
          Use the input panel to generate an IEEE paper with diagrams and equations
        </p>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Generation Success Banner */}
      <Card className="p-4 bg-green-50 border-green-200">
        <div className="flex items-start gap-3">
          <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium text-green-900">Paper Generated Successfully!</p>
            <p className="text-sm text-green-800 mt-1">
              Your IEEE-formatted paper is ready for download and use.
            </p>
          </div>
        </div>
      </Card>

      {/* Preview Tabs */}
      <Card>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-5 border-b">
            <TabsTrigger value="overview" className="relative">
              Overview
            </TabsTrigger>
            <TabsTrigger value="diagrams" className="relative">
              Diagrams
              {diagrams.length > 0 && (
                <Badge variant="secondary" className="ml-2 h-5 w-5 flex items-center justify-center p-0 text-xs">
                  {diagrams.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="equations" className="relative">
              Equations
              {equations.length > 0 && (
                <Badge variant="secondary" className="ml-2 h-5 w-5 flex items-center justify-center p-0 text-xs">
                  {equations.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="content">Content</TabsTrigger>
            <TabsTrigger value="source">LaTeX</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                <div className="flex items-center gap-2 mb-2">
                  <Image className="h-4 w-4 text-blue-600" />
                  <p className="text-sm font-medium text-blue-900">Diagrams</p>
                </div>
                <p className="text-2xl font-bold text-blue-600">{diagrams.length}</p>
              </div>

              <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                <div className="flex items-center gap-2 mb-2">
                  <Sigma className="h-4 w-4 text-purple-600" />
                  <p className="text-sm font-medium text-purple-900">Equations</p>
                </div>
                <p className="text-2xl font-bold text-purple-600">{equations.length}</p>
              </div>
            </div>

            {references && (
              <div className="bg-gray-50 p-4 rounded-lg border">
                <p className="text-sm font-medium mb-3">Reference Statistics</p>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <p className="text-gray-500">Figures</p>
                    <p className="font-semibold">{references.total_figures || 0}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Equations</p>
                    <p className="font-semibold">{references.total_equations || 0}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Citations</p>
                    <p className="font-semibold">{references.total_citations || 0}</p>
                  </div>
                </div>
              </div>
            )}

            {keywords.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-2">Keywords</p>
                <div className="flex flex-wrap gap-2">
                  {keywords.map((kw, i) => (
                    <Badge key={i} variant="secondary">
                      {kw}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-2 pt-4 border-t">
              <p className="text-sm font-medium">Downloads</p>
              <Button
                onClick={handleDownloadPDF}
                disabled={!pdfPath}
                className="w-full justify-start"
                variant="outline"
              >
                <Download className="h-4 w-4 mr-2" />
                Download IEEE PDF
              </Button>
              <Button
                onClick={handleDownloadLaTeX}
                disabled={!latexSource}
                className="w-full justify-start"
                variant="outline"
              >
                <FileText className="h-4 w-4 mr-2" />
                Download LaTeX Source
              </Button>
            </div>
          </TabsContent>

          {/* Diagrams Tab */}
          <TabsContent value="diagrams" className="p-6">
            {diagrams.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No diagrams in this paper</p>
            ) : (
              <div className="space-y-4">
                {diagrams.map((diagram, idx) => (
                  <Card key={idx} className="p-4 border">
                    <div className="flex gap-4">
                      <div className="flex-shrink-0">
                        <img
                          src={`/generated_assets/${diagram.filename}`}
                          alt={diagram.caption}
                          className="h-24 w-32 object-cover rounded bg-gray-100"
                        />
                      </div>
                      <div className="flex-1">
                        <Badge variant="outline" className="mb-2">
                          {diagram.label}
                        </Badge>
                        <p className="font-medium text-sm">{diagram.caption}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          Width: {(diagram.width * 100).toFixed(0)}% of column
                        </p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Equations Tab */}
          <TabsContent value="equations" className="p-6">
            {equations.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No equations in this paper</p>
            ) : (
              <div className="space-y-4">
                {equations.map((eq, idx) => (
                  <Card key={idx} className="p-4 border">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <Badge variant="outline" className="mb-2">
                          Eq. {eq.equation_number}
                        </Badge>
                        <code className="text-sm font-mono bg-gray-50 p-2 block rounded my-2 overflow-x-auto">
                          {eq.latex_equation || eq.original_input}
                        </code>
                        {eq.explanation && (
                          <p className="text-sm text-gray-600 mt-2">{eq.explanation}</p>
                        )}
                        {Object.keys(eq.variables).length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs font-medium text-gray-500 mb-1">Variables:</p>
                            <div className="text-xs space-y-1">
                              {Object.entries(eq.variables).map(([varName, varDesc]) => (
                                <p key={varName}>
                                  <code className="font-mono">{varName}</code>: {varDesc}
                                </p>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Content Tab */}
          <TabsContent value="content" className="p-6">
            <div className="space-y-3">
              <Button
                onClick={handleCopyContent}
                variant="outline"
                size="sm"
                className="w-full"
              >
                Copy All Content
              </Button>
              <ScrollArea className="h-96 border rounded-lg p-4 bg-gray-50">
                <pre className="text-xs whitespace-pre-wrap font-mono">
                  {content || 'No content available'}
                </pre>
              </ScrollArea>
            </div>
          </TabsContent>

          {/* LaTeX Source Tab */}
          <TabsContent value="source" className="p-6">
            <div className="space-y-3">
              <Button
                onClick={handleDownloadLaTeX}
                variant="outline"
                size="sm"
                className="w-full"
              >
                Download LaTeX
              </Button>
              <ScrollArea className="h-96 border rounded-lg p-4 bg-gray-50">
                <pre className="text-xs whitespace-pre-wrap font-mono">
                  {latexSource ? latexSource.substring(0, 2000) + '...' : 'Loading...'}
                </pre>
              </ScrollArea>
            </div>
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  )
}
