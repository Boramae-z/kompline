"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileCode, Play } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { analyzeCode, type AnalyzeResponse } from "@/lib/api";

const SAMPLE_CODE_COMPLIANT = `"""Compliant deposit ranking algorithm."""

RANKING_WEIGHTS = {
    "interest_rate": 0.5,
    "accessibility": 0.2,
    "term_flexibility": 0.15,
    "stability": 0.15,
}

def rank_deposits(products, stability_ratings=None):
    """Rank deposits by documented, fair criteria."""
    scored = []
    for product in products:
        score = (
            RANKING_WEIGHTS["interest_rate"] * product.interest_rate / 10
            + RANKING_WEIGHTS["accessibility"] * 0.5
            + RANKING_WEIGHTS["term_flexibility"] * 0.5
            + RANKING_WEIGHTS["stability"] * stability_ratings.get(product.bank, 0.5)
        )
        scored.append((product, score))
    return sorted(scored, key=lambda x: x[1], reverse=True)
`;

const SAMPLE_CODE_ISSUES = `"""Ranking with compliance issues."""
import random

def rank_deposits_biased(products, preferred_banks=None):
    """WARNING: Contains undocumented preferences."""
    scored = []
    for product in products:
        score = product.interest_rate / 10

        # ISSUE: Undocumented affiliate boost
        if product.is_affiliated:
            score *= 1.2

        # ISSUE: Hidden preference
        if product.bank in (preferred_banks or []):
            score *= 1.1

        scored.append((product, score))

    # ISSUE: Undisclosed randomization
    random.shuffle(scored)
    return sorted(scored, key=lambda x: x[1], reverse=True)
`;

const availableCompliances = [
  { id: "byeolji5-fairness", name: "Byeolji5 Algorithm Fairness", description: "Korean financial regulation for algorithm fairness" },
  { id: "pipa-kr-2024", name: "PIPA (Korea)", description: "Personal Information Protection Act" },
];

export default function NewAuditPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [selectedCompliances, setSelectedCompliances] = useState<string[]>(["byeolji5-fairness"]);
  const [useLLM, setUseLLM] = useState(true);
  const [requireReview, setRequireReview] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setCode(event.target?.result as string);
      };
      reader.readAsText(file);
    }
  };

  const toggleCompliance = (id: string) => {
    setSelectedCompliances((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const handleSubmit = async () => {
    if (!code.trim()) {
      setError("Please enter or upload source code");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response: AnalyzeResponse = await analyzeCode({
        source_code: code,
        compliance_ids: selectedCompliances,
        use_llm: useLLM,
        require_review: requireReview,
      });

      if (response.success) {
        // Store result in sessionStorage for the detail page
        sessionStorage.setItem("lastAuditResult", JSON.stringify(response));
        router.push("/audits/latest");
      } else {
        setError(response.error || "Analysis failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start audit");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Header
        title="New Audit"
        description="Start a new compliance audit"
      />

      <div className="p-6 space-y-6">
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Code Input - 2 columns */}
          <div className="lg:col-span-2 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Source Code</CardTitle>
                <CardDescription>
                  Enter or upload the Python code to analyze
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* File Upload */}
                <div className="flex items-center gap-4">
                  <label className="flex-1">
                    <input
                      type="file"
                      accept=".py"
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                    <div className="flex items-center justify-center gap-2 rounded-lg border-2 border-dashed p-4 cursor-pointer hover:border-primary/50 transition-colors">
                      <Upload className="h-5 w-5 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">
                        Upload .py file
                      </span>
                    </div>
                  </label>
                </div>

                {/* Sample Code Buttons */}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCode(SAMPLE_CODE_COMPLIANT)}
                  >
                    <FileCode className="h-4 w-4 mr-2" />
                    Load Compliant Sample
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCode(SAMPLE_CODE_ISSUES)}
                  >
                    <FileCode className="h-4 w-4 mr-2" />
                    Load Non-compliant Sample
                  </Button>
                </div>

                {/* Code Editor */}
                <textarea
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Paste your Python code here..."
                  className="w-full h-96 p-4 rounded-lg border bg-muted/50 font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </CardContent>
            </Card>
          </div>

          {/* Settings - 1 column */}
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Compliance Selection</CardTitle>
                <CardDescription>
                  Select regulations to audit against
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {availableCompliances.map((compliance) => (
                  <label
                    key={compliance.id}
                    className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                      selectedCompliances.includes(compliance.id)
                        ? "border-primary bg-primary/5"
                        : "hover:border-primary/50"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedCompliances.includes(compliance.id)}
                      onChange={() => toggleCompliance(compliance.id)}
                      className="mt-1"
                    />
                    <div>
                      <p className="font-medium text-sm">{compliance.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {compliance.description}
                      </p>
                    </div>
                  </label>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Options</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={useLLM}
                    onChange={(e) => setUseLLM(e.target.checked)}
                  />
                  <div>
                    <p className="text-sm font-medium">Use LLM Evaluation</p>
                    <p className="text-xs text-muted-foreground">
                      More accurate but slower
                    </p>
                  </div>
                </label>

                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={requireReview}
                    onChange={(e) => setRequireReview(e.target.checked)}
                  />
                  <div>
                    <p className="text-sm font-medium">Enable Human-in-the-Loop</p>
                    <p className="text-xs text-muted-foreground">
                      Flag uncertain findings for review
                    </p>
                  </div>
                </label>
              </CardContent>
            </Card>

            {/* Error */}
            {error && (
              <div className="rounded-lg bg-destructive/10 p-4 text-sm text-destructive">
                {error}
              </div>
            )}

            {/* Submit */}
            <Button
              className="w-full"
              size="lg"
              onClick={handleSubmit}
              disabled={loading || !code.trim() || selectedCompliances.length === 0}
            >
              {loading ? (
                <>
                  <span className="animate-spin mr-2">⏳</span>
                  Analyzing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Start Audit
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
