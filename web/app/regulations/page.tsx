"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, Globe, Tag, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { listCompliances, type Compliance } from "@/lib/api";

export default function RegulationsPage() {
  const [compliances, setCompliances] = useState<Compliance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchCompliances() {
      try {
        const data = await listCompliances();
        setCompliances(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "규정을 불러올 수 없습니다");
      } finally {
        setLoading(false);
      }
    }
    fetchCompliances();
  }, []);

  if (loading) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">규정 목록</h1>
          <p className="text-muted-foreground">사용 가능한 컴플라이언스 규정</p>
        </div>
        <div className="text-center py-8">
          <p className="text-destructive">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">규정 목록</h1>
        <p className="text-muted-foreground">사용 가능한 컴플라이언스 규정</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {compliances.map((compliance) => (
          <Card
            key={compliance.id}
            className="h-full hover:shadow-md transition-shadow"
          >
            <CardHeader className="pb-2">
              <div className="flex items-start gap-3">
                <FileText className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                <CardTitle className="text-lg font-medium line-clamp-2">
                  {compliance.name}
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground line-clamp-3 mb-3">
                {compliance.description}
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="flex items-center gap-1">
                  <Globe className="h-3 w-3" />
                  {compliance.jurisdiction}
                </Badge>
                <Badge variant="secondary" className="flex items-center gap-1">
                  <Tag className="h-3 w-3" />
                  {compliance.category}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
        {compliances.length === 0 && (
          <div className="col-span-full text-center py-8">
            <p className="text-muted-foreground">등록된 규정이 없습니다.</p>
          </div>
        )}
      </div>
    </div>
  );
}
