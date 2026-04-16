/**
 * Diagram Uploader Component
 * ──────────────────────────
 * Handles drag-and-drop diagram upload with preview and metadata input.
 */

'use client'

import React, { useState, useRef } from 'react'
import { Upload, X, Image as ImageIcon } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

export interface DiagramData {
  base64: string
  caption: string
  label: string
  width: number
  preview?: string
}

interface DiagramUploaderProps {
  onDiagramsChange: (diagrams: DiagramData[]) => void
  maxDiagrams?: number
}

export function DiagramUploader({ onDiagramsChange, maxDiagrams = 5 }: DiagramUploaderProps) {
  const [diagrams, setDiagrams] = useState<DiagramData[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editCaption, setEditCaption] = useState('')
  const [editLabel, setEditLabel] = useState('')

  const handleFiles = async (files: FileList) => {
    const fileArray = Array.from(files)
    
    for (const file of fileArray) {
      if (diagrams.length >= maxDiagrams) break
      
      // Validate file type
      if (!['image/png', 'image/jpeg', 'image/svg+xml'].includes(file.type)) {
        console.warn(`Unsupported file type: ${file.type}`)
        continue
      }
      
      // Validate file size (10MB)
      if (file.size > 10 * 1024 * 1024) {
        console.warn(`File too large: ${file.name}`)
        continue
      }
      
      // Convert to base64
      const reader = new FileReader()
      reader.onload = (e) => {
        const base64 = e.target?.result as string
        const newDiagram: DiagramData = {
          base64,
          caption: `Figure ${diagrams.length + 1}`,
          label: `fig:diagram_${diagrams.length + 1}`,
          width: 0.9,
          preview: base64,
        }
        
        const updatedDiagrams = [...diagrams, newDiagram]
        setDiagrams(updatedDiagrams)
        onDiagramsChange(updatedDiagrams)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(e.target.files)
    }
  }

  const removeDiagram = (index: number) => {
    const updated = diagrams.filter((_, i) => i !== index)
    setDiagrams(updated)
    onDiagramsChange(updated)
  }

  const startEdit = (index: number) => {
    setEditingIndex(index)
    setEditCaption(diagrams[index].caption)
    setEditLabel(diagrams[index].label)
  }

  const saveEdit = (index: number) => {
    const updated = [...diagrams]
    updated[index].caption = editCaption
    updated[index].label = editLabel.startsWith('fig:') ? editLabel : `fig:${editLabel}`
    setDiagrams(updated)
    onDiagramsChange(updated)
    setEditingIndex(null)
  }

  return (
    <div className="space-y-4">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
        }`}
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <Upload className="mx-auto mb-2 h-8 w-8 text-gray-400" />
        <p className="text-sm font-semibold text-gray-700">
          Drag and drop diagrams here
        </p>
        <p className="text-xs text-gray-500">
          PNG, JPG, SVG • Max 10MB • Max {maxDiagrams} diagrams
        </p>
        <Button
          variant="outline"
          size="sm"
          className="mt-4"
          onClick={() => fileInputRef.current?.click()}
        >
          Select Files
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          hidden
          accept="image/png,image/jpeg,image/svg+xml"
          onChange={handleInputChange}
        />
      </div>

      {/* Diagram List */}
      <div className="space-y-3">
        {diagrams.map((diagram, index) => (
          <Card key={index} className="p-4">
            {editingIndex === index ? (
              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium">Caption</label>
                  <Textarea
                    value={editCaption}
                    onChange={(e) => setEditCaption(e.target.value)}
                    placeholder="Figure caption..."
                    rows={2}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">LaTeX Label</label>
                  <Input
                    value={editLabel}
                    onChange={(e) => setEditLabel(e.target.value)}
                    placeholder="fig:name"
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => saveEdit(index)}
                  >
                    Save
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setEditingIndex(null)}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex gap-4">
                <div className="flex-shrink-0">
                  {diagram.preview && diagram.preview.includes('data:image') ? (
                    <img
                      src={diagram.preview}
                      alt={diagram.caption}
                      className="h-20 w-20 object-cover rounded border"
                    />
                  ) : (
                    <div className="h-20 w-20 flex items-center justify-center bg-gray-100 rounded">
                      <ImageIcon className="h-8 w-8 text-gray-400" />
                    </div>
                  )}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-sm">{diagram.caption}</p>
                  <p className="text-xs text-gray-500">{diagram.label}</p>
                  <p className="text-xs text-gray-400">Width: {(diagram.width * 100).toFixed(0)}%</p>
                </div>
                <div className="flex gap-2 self-center">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => startEdit(index)}
                  >
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => removeDiagram(index)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </Card>
        ))}
      </div>

      <p className="text-xs text-gray-500">
        {diagrams.length} of {maxDiagrams} diagrams added
      </p>
    </div>
  )
}
