'use client';

import { useState } from 'react';
import { Download, Eye, Loader2, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import type { TaskStatus } from '@/types';

interface IEEEPreviewProps {
  taskId: string;
  status?: TaskStatus;
}

export function IEEEPreview({ taskId, status }: IEEEPreviewProps) {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  const [latexPreview, setLatexPreview] = useState<string>('');
  const [isLoadingLatex, setIsLoadingLatex] = useState(false);
  const [isCompilingPdf, setIsCompilingPdf] = useState(false);
  const [error, setError] = useState<string>('');
  const [previewInfo, setPreviewInfo] = useState<any>(null);
  const [validationResult, setValidationResult] = useState<any>(null);

  const loadIEEEPreview = async () => {
    setIsLoadingLatex(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/langgraph/ieee-preview/${taskId}`);
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to load preview');
      }
      const data = await res.json();
      setLatexPreview(data.latex_source);
      setPreviewInfo({
        sections: data.sections_count,
        equations: data.equations_count,
        diagrams: data.diagrams_count,
        references: data.references_count,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load preview');
    } finally {
      setIsLoadingLatex(false);
    }
  };

  const compilePdf = async () => {
    setIsCompilingPdf(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/langgraph/compile-pdf/${taskId}`, {
        method: 'POST',
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'PDF compilation failed');
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'paper.pdf';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'PDF compilation failed');
    } finally {
      setIsCompilingPdf(false);
    }
  };

  const validateFormat = async () => {
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/langgraph/ieee-validate/${taskId}`);
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Validation failed');
      }
      const data = await res.json();
      setValidationResult(data.validation);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Validation failed');
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Eye className="h-5 w-5" />
          IEEE Paper Preview
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 flex-wrap">
          <Button
            onClick={loadIEEEPreview}
            disabled={isLoadingLatex}
            variant="outline"
          >
            {isLoadingLatex ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Loading...
              </>
            ) : (
              <>
                <Eye className="h-4 w-4 mr-2" />
                Load LaTeX Preview
              </>
            )}
          </Button>

          <Button
            onClick={compilePdf}
            disabled={isCompilingPdf || !latexPreview}
            variant="default"
          >
            {isCompilingPdf ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Compiling...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Download PDF
              </>
            )}
          </Button>

          <Button
            onClick={validateFormat}
            disabled={!latexPreview}
            variant="outline"
          >
            Validate Format
          </Button>
        </div>

        {/* Preview Info */}
        {previewInfo && (
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-blue-50 p-3 rounded-lg">
              <p className="text-sm text-gray-600">Sections</p>
              <p className="text-2xl font-bold text-blue-600">
                {previewInfo.sections}
              </p>
            </div>
            <div className="bg-purple-50 p-3 rounded-lg">
              <p className="text-sm text-gray-600">Equations</p>
              <p className="text-2xl font-bold text-purple-600">
                {previewInfo.equations}
              </p>
            </div>
            <div className="bg-green-50 p-3 rounded-lg">
              <p className="text-sm text-gray-600">Figures</p>
              <p className="text-2xl font-bold text-green-600">
                {previewInfo.diagrams}
              </p>
            </div>
            <div className="bg-orange-50 p-3 rounded-lg">
              <p className="text-sm text-gray-600">References</p>
              <p className="text-2xl font-bold text-orange-600">
                {previewInfo.references}
              </p>
            </div>
          </div>
        )}

        {/* Validation Results */}
        {validationResult && (
          <Card className="bg-gray-50">
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <span
                  className={`w-3 h-3 rounded-full ${
                    validationResult.is_valid ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                Format Validation
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="font-medium">Title:</span>{' '}
                  <Badge
                    variant={validationResult.has_title ? 'default' : 'destructive'}
                  >
                    {validationResult.has_title ? '✓' : '✗'}
                  </Badge>
                </div>
                <div>
                  <span className="font-medium">Authors:</span>{' '}
                  <Badge
                    variant={validationResult.has_author ? 'default' : 'destructive'}
                  >
                    {validationResult.has_author ? '✓' : '✗'}
                  </Badge>
                </div>
                <div>
                  <span className="font-medium">Abstract:</span>{' '}
                  <Badge
                    variant={validationResult.has_abstract ? 'default' : 'destructive'}
                  >
                    {validationResult.has_abstract ? '✓' : '✗'}
                  </Badge>
                </div>
                <div>
                  <span className="font-medium">Sections:</span>{' '}
                  <Badge variant="outline">{validationResult.section_count}</Badge>
                </div>
              </div>

              {validationResult.errors && validationResult.errors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded p-2">
                  <p className="font-medium text-red-900 mb-2">Issues Found:</p>
                  <ul className="space-y-1">
                    {validationResult.errors.map((error: string, i: number) => (
                      <li key={i} className="text-red-800 text-xs">
                        • {error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* LaTeX Source Preview */}
        {latexPreview && (
          <Tabs defaultValue="source" className="w-full">
            <TabsList>
              <TabsTrigger value="source">LaTeX Source</TabsTrigger>
              <TabsTrigger value="info">Document Info</TabsTrigger>
            </TabsList>

            <TabsContent value="source" className="space-y-4">
              <div className="bg-gray-900 text-gray-100 rounded-lg p-4 font-mono text-xs overflow-x-auto max-h-96 overflow-y-auto">
                <pre>{latexPreview.substring(0, 2000)}...</pre>
              </div>
              <p className="text-xs text-gray-500">
                Showing first 2000 characters of LaTeX source
              </p>
            </TabsContent>

            <TabsContent value="info" className="space-y-4">
              <div className="grid gap-4">
                <div>
                  <h4 className="font-medium mb-2">Document Properties</h4>
                  <ul className="space-y-2 text-sm">
                    <li>
                      <span className="font-medium">Document Class:</span> IEEEtran
                      (conference)
                    </li>
                    <li>
                      <span className="font-medium">Layout:</span> Two-column
                    </li>
                    <li>
                      <span className="font-medium">Font:</span> Times New Roman
                    </li>
                    <li>
                      <span className="font-medium">Format:</span> IEEE Conference
                    </li>
                  </ul>
                </div>

                {previewInfo && (
                  <div>
                    <h4 className="font-medium mb-2">Paper Contents</h4>
                    <ul className="space-y-2 text-sm">
                      <li>
                        <span className="font-medium">Sections:</span>{' '}
                        {previewInfo.sections}
                      </li>
                      <li>
                        <span className="font-medium">Equations:</span>{' '}
                        {previewInfo.equations}
                      </li>
                      <li>
                        <span className="font-medium">Figures:</span>{' '}
                        {previewInfo.diagrams}
                      </li>
                      <li>
                        <span className="font-medium">References:</span>{' '}
                        {previewInfo.references}
                      </li>
                    </ul>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        )}

        {/* IEEE Standards Info */}
        <Alert>
          <AlertDescription className="text-xs space-y-2">
            <p className="font-medium">IEEE Paper Format</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Official IEEEtran conference template</li>
              <li>Two-column layout with balanced columns</li>
              <li>Numbered sections and automatic equation/figure numbering</li>
              <li>IEEE reference style ([1], [2], etc.)</li>
              <li>Optimized for conference proceedings</li>
            </ul>
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
}
