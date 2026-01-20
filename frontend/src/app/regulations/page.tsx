
"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { supabase } from "@/lib/supabase"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

export default function RegulationsPage() {
    const [documents, setDocuments] = useState<any[]>([])

    useEffect(() => {
        async function fetchDocuments() {
            const { data, error } = await supabase
                .from('documents')
                .select('*')

            if (!error && data) {
                setDocuments(data)
            }
        }
        fetchDocuments()
    }, [])

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Regulations</h1>
                <p className="text-muted-foreground">Available compliance documents.</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {documents.map((doc) => (
                    <Link key={doc.id} href={`/regulations/${doc.id}`} className="block h-full">
                        <Card className="h-full hover:shadow-md transition-shadow cursor-pointer">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-lg font-medium truncate" title={doc.filename}>
                                    {doc.filename}
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex gap-2 mb-2">
                                    <Badge variant="outline">{doc.language}</Badge>
                                    <Badge variant="secondary">{doc.page_count} Pages</Badge>
                                </div>
                                <p className="text-xs text-muted-foreground line-clamp-3">
                                    Imported on {new Date(doc.created_at || Date.now()).toLocaleDateString()}
                                </p>
                            </CardContent>
                        </Card>
                    </Link>
                ))}
                {documents.length === 0 && (
                    <p className="text-muted-foreground">No regulations loaded.</p>
                )}
            </div>
        </div>
    )
}
