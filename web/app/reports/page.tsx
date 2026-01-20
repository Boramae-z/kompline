"use client";

import { FileText, Download, Calendar } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

// Mock data for demo
const mockReports = [
  {
    id: "report-001",
    name: "Algorithm Fairness Audit Report",
    compliance: "byeolji5-fairness",
    createdAt: new Date().toISOString(),
    status: "pass",
    format: "PDF",
  },
  {
    id: "report-002",
    name: "PIPA Compliance Report",
    compliance: "pipa-kr-2024",
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    status: "fail",
    format: "Markdown",
  },
];

export default function ReportsPage() {
  return (
    <div className="min-h-screen">
      <Header
        title="Reports"
        description="Generated compliance reports"
      />

      <div className="p-6 space-y-6">
        {/* Reports List */}
        <div className="space-y-3">
          {mockReports.map((report) => (
            <Card key={report.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="rounded-lg bg-primary/10 p-2">
                      <FileText className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">{report.name}</p>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>{report.compliance}</span>
                        <span>·</span>
                        <Calendar className="h-3 w-3" />
                        <span>{formatDate(report.createdAt)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Badge variant={report.status === "pass" ? "success" : "error"}>
                      {report.status.toUpperCase()}
                    </Badge>
                    <Badge variant="outline">{report.format}</Badge>
                    <Button variant="outline" size="sm">
                      <Download className="h-4 w-4 mr-2" />
                      Download
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {mockReports.length === 0 && (
          <Card>
            <CardContent className="p-12 text-center">
              <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium">No reports yet</h3>
              <p className="text-muted-foreground mt-2">
                Reports will appear here after completing audits.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
