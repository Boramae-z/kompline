"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, XCircle, MessageSquare } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FindingCard } from "@/components/findings/finding-card";
import { getPendingReviews, type Finding } from "@/lib/api";

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "fail" | "review">("all");

  useEffect(() => {
    async function loadReviews() {
      try {
        const data = await getPendingReviews();
        setReviews(data);
      } catch (error) {
        console.error("Failed to load reviews:", error);
      } finally {
        setLoading(false);
      }
    }
    loadReviews();
  }, []);

  const handleApprove = (id: string) => {
    setReviews((prev) => prev.filter((r) => r.id !== id));
    // TODO: Call API to approve
  };

  const handleReject = (id: string) => {
    setReviews((prev) => prev.filter((r) => r.id !== id));
    // TODO: Call API to reject
  };

  const handleRequestContext = (id: string) => {
    // TODO: Open modal to request context
    console.log("Request context for:", id);
  };

  const filteredReviews = reviews.filter((r) => {
    if (filter === "all") return true;
    return r.status === filter;
  });

  const failCount = reviews.filter((r) => r.status === "fail").length;
  const reviewCount = reviews.filter((r) => r.status === "review").length;

  return (
    <div className="min-h-screen">
      <Header
        title="Review Queue"
        description="Human-in-the-loop review for uncertain findings"
      />

      <div className="p-6 space-y-6">
        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Pending</p>
                  <p className="text-2xl font-bold">{reviews.length}</p>
                </div>
                <AlertTriangle className="h-8 w-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Failed Findings</p>
                  <p className="text-2xl font-bold">{failCount}</p>
                </div>
                <XCircle className="h-8 w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Need Review</p>
                  <p className="text-2xl font-bold">{reviewCount}</p>
                </div>
                <MessageSquare className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <div className="flex gap-2">
          <Button
            variant={filter === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("all")}
          >
            All ({reviews.length})
          </Button>
          <Button
            variant={filter === "fail" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("fail")}
          >
            <XCircle className="h-4 w-4 mr-1" />
            Failed ({failCount})
          </Button>
          <Button
            variant={filter === "review" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("review")}
          >
            <AlertTriangle className="h-4 w-4 mr-1" />
            Review ({reviewCount})
          </Button>
        </div>

        {/* Review List */}
        {loading ? (
          <div className="flex items-center justify-center p-12">
            <p className="text-muted-foreground">Loading reviews...</p>
          </div>
        ) : filteredReviews.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium">All caught up!</h3>
              <p className="text-muted-foreground mt-2">
                No pending reviews at the moment.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {filteredReviews.map((finding) => (
              <FindingCard
                key={finding.id}
                finding={finding}
                showActions={true}
                onApprove={handleApprove}
                onReject={handleReject}
                onRequestContext={handleRequestContext}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
