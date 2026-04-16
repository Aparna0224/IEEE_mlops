/**
 * IEEE Paper Generation Page
 * ──────────────────────────
 * Complete page for generating IEEE papers with diagrams,
 * equations, and structured research content.
 */

'use client'

import React, { useState, useEffect } from 'react'
import { ResearchInputPanel, ResearchInputData, IEEEPaperPreview } from '@/components/ieee'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface PaperGenerationResponse {
  task_id: string
  status: string
  progress: number
  message: string
  pdf_path?: string
  latex_source?: string
  content?: string
  diagrams?: any[]
  equations?: any[]
  references?: Record<string, number>
  keywords?: string[]
  error?: string
}

export default function IEEEPaperGeneratorPage() {
  const [generationData, setGenerationData] = useState<ResearchInputData | null>(null)
  const [status, setStatus] = useState<PaperGenerationResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null)

  // Poll for generation status
  useEffect(() => {
    if (!taskId) return

    const poll = setInterval(async () => {
      try {
        const response = await fetch(`/api/ieee/status/${taskId}`)
        if (response.ok) {
          const data = await response.json()
          setStatus(data)

          // Stop polling if completed or failed
          if (data.status === 'completed' || data.status === 'failed') {
            if (pollInterval) clearInterval(pollInterval)
            setIsLoading(false)
          }
        }
      } catch (err) {
        console.error('Error polling status:', err)
      }
    }, 2000) // Poll every 2 seconds

    setPollInterval(poll)

    return () => clearInterval(poll)
  }, [taskId, pollInterval])

  const handleGenerate = async (data: ResearchInputData) => {
    setGenerationData(data)
    setIsLoading(true)
    setError(null)
    setStatus(null)

    try {
      // Prepare request payload
      const payload = {
        topic: data.topic,
        diagrams: data.diagrams,
        equations: data.equations,
        notes: data.notes,
        authors: data.authors,
        max_references: data.maxReferences,
        model_name: data.model,
      }

      // Send generation request
      const response = await fetch('/api/ieee/generate-paper', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error(`Generation failed: ${response.statusText}`)
      }

      const result = await response.json()
      setTaskId(result.task_id)
      setStatus(result)

    } catch (err) {
      setIsLoading(false)
      setError(err instanceof Error ? err.message : 'Generation failed')
      console.error('Error:', err)
    }
  }

  const handleReset = () => {
    setGenerationData(null)
    setStatus(null)
    setTaskId(null)
    setError(null)
    setIsLoading(false)
    if (pollInterval) clearInterval(pollInterval)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-slate-900">IEEE Paper Generator</h1>
              <p className="text-lg text-slate-600 mt-1">
                Create comprehensive IEEE-formatted papers with diagrams, equations, and calculations
              </p>
            </div>
            {taskId && (
              <Badge variant="outline" className="text-xs">
                Task: {taskId}
              </Badge>
            )}
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <Card className="p-4 bg-red-50 border-red-200">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
              <div>
                <p className="font-medium text-red-900">Error</p>
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
          </Card>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Input Panel */}
          <div>
            <ResearchInputPanel
              onGenerate={handleGenerate}
              isLoading={isLoading}
            />
          </div>

          {/* Preview Panel */}
          <div>
            {status && (
              <div className="space-y-4">
                {/* Progress Info */}
                {isLoading && (
                  <Card className="p-4 bg-blue-50 border-blue-200">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-blue-900">Generating Paper</p>
                        <span className="text-sm font-semibold text-blue-600">{status.progress}%</span>
                      </div>
                      <div className="w-full bg-blue-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${status.progress}%` }}
                        />
                      </div>
                      <p className="text-xs text-blue-800">{status.message}</p>
                    </div>
                  </Card>
                )}

                {/* Paper Preview */}
                <IEEEPaperPreview
                  taskId={taskId || ''}
                  pdfPath={status.pdf_path}
                  latexSource={status.latex_source}
                  content={status.content}
                  diagrams={status.diagrams}
                  equations={status.equations}
                  references={status.references}
                  keywords={status.keywords}
                  isGenerated={status.status === 'completed'}
                  isLoading={isLoading}
                  error={status.error}
                />

                {/* Reset Button */}
                {!isLoading && status.status === 'completed' && (
                  <Button
                    onClick={handleReset}
                    variant="outline"
                    className="w-full"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Generate Another Paper
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <Card className="p-4 bg-slate-50 border-slate-200">
          <div className="text-sm text-slate-600 space-y-2">
            <p>
              <strong>💡 Tips:</strong>
            </p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>Provide a clear, specific research topic for best results</li>
              <li>Upload diagrams as PNG or JPG with descriptive captions</li>
              <li>Enter equations in simple notation (e.g., S_i = 1/N * sum(x_i)) or LaTeX</li>
              <li>Add notes to guide the paper generation towards your focus areas</li>
              <li>IEEE formatting is automatically applied to the generated PDF</li>
            </ul>
          </div>
        </Card>
      </div>
    </div>
  )
}
