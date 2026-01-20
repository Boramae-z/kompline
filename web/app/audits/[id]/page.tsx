"use client";

import { useParams } from "next/navigation";
import { redirect } from "next/navigation";

export default function AuditDetailPage() {
  const params = useParams();
  const id = params.id as string;

  // For demo, redirect "latest" to the latest page
  // In production, this would fetch audit by ID
  if (id === "latest") {
    redirect("/audits/latest");
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h2 className="text-xl font-semibold">Audit: {id}</h2>
        <p className="text-muted-foreground mt-2">
          Audit detail view will be implemented with persistent storage.
        </p>
      </div>
    </div>
  );
}
