"use client";

import { useState, useRef } from "react";
import { Upload, Trash2, Plus, ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DiagramInfo } from "@/types";

interface DiagramUploaderProps {
  diagrams: DiagramInfo[];
  onAdd: (diagram: DiagramInfo) => void;
  onRemove: (id: string) => void;
  onUpdate: (id: string, field: keyof DiagramInfo, value: any) => void;
}

export function DiagramUploader({
  diagrams,
  onAdd,
  onRemove,
  onUpdate,
}: DiagramUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [newDiagram, setNewDiagram] = useState<Partial<DiagramInfo>>({
    label: "",
    caption: "",
    file: undefined,
  });
  const [preview, setPreview] = useState<string | null>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && ["image/png", "image/jpeg", "image/svg+xml"].includes(file.type)) {
      setNewDiagram((p) => ({ ...p, file }));
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleAdd = () => {
    if (
      newDiagram.label &&
      newDiagram.caption &&
      newDiagram.file
    ) {
      const diagram: DiagramInfo = {
        id: `fig-${Date.now()}`,
        label: newDiagram.label as string,
        caption: newDiagram.caption as string,
        file: newDiagram.file as File,
      };
      onAdd(diagram);
      setNewDiagram({ label: "", caption: "", file: undefined });
      setPreview(null);
      setIsAdding(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Diagrams & Figures</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {diagrams.length > 0 && (
          <div className="space-y-3">
            {diagrams.map((diagram) => (
              <div
                key={diagram.id}
                className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-900"
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                  <div>
                    <label className="text-sm font-medium">Label</label>
                    <Input
                      value={diagram.label}
                      onChange={(e) =>
                        onUpdate(diagram.id, "label", e.target.value)
                      }
                      placeholder="e.g., fig:architecture"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="text-sm font-medium">Caption</label>
                    <Input
                      value={diagram.caption}
                      onChange={(e) =>
                        onUpdate(diagram.id, "caption", e.target.value)
                      }
                      placeholder="Brief description of the diagram"
                    />
                  </div>
                </div>
                {typeof diagram.file === "string" && (
                  <div className="mb-3">
                    <div className="relative w-full h-40 bg-gray-100 dark:bg-gray-700 rounded border border-gray-300">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={diagram.file}
                        alt={diagram.caption}
                        className="w-full h-full object-contain"
                      />
                    </div>
                  </div>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onRemove(diagram.id)}
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
                  value={newDiagram.label as string}
                  onChange={(e) =>
                    setNewDiagram((p) => ({
                      ...p,
                      label: e.target.value,
                    }))
                  }
                  placeholder="e.g., fig:system-arch"
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-sm font-medium">Caption</label>
                <Input
                  value={newDiagram.caption as string}
                  onChange={(e) =>
                    setNewDiagram((p) => ({
                      ...p,
                      caption: e.target.value,
                    }))
                  }
                  placeholder="Description for IEEE caption"
                />
              </div>
            </div>

            <div className="mb-4">
              <label className="text-sm font-medium block mb-2">Upload Image</label>
              <div className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                onClick={() => fileInputRef.current?.click()}
              >
                <ImageIcon className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Click to upload PNG, JPG, or SVG
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".png,.jpg,.jpeg,.svg"
                  onChange={handleFileSelect}
                  hidden
                />
              </div>
            </div>

            {preview && (
              <div className="mb-4">
                <p className="text-sm font-medium mb-2">Preview</p>
                <div className="relative w-full h-32 bg-gray-100 dark:bg-gray-700 rounded border">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={preview}
                    alt="preview"
                    className="w-full h-full object-contain"
                  />
                </div>
              </div>
            )}

            <div className="flex gap-2">
              <Button onClick={handleAdd} className="bg-blue-600">
                Add Diagram
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setIsAdding(false);
                  setNewDiagram({ label: "", caption: "", file: undefined });
                  setPreview(null);
                  if (fileInputRef.current) fileInputRef.current.value = "";
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
            <Plus className="w-4 h-4 mr-2" /> Add Diagram
          </Button>
        )}

        <div className="text-xs text-gray-500 mt-4">
          📌 Supported formats: PNG, JPG, SVG (max 10MB)
        </div>
      </CardContent>
    </Card>
  );
}
