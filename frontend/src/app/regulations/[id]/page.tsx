
"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { supabase } from "@/lib/supabase"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Loader2 } from "lucide-react"

export default function RegulationDetailPage() {
    const params = useParams()
    const id = params.id as string

    const [document, setDocument] = useState<any>(null)
    const [items, setItems] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        async function fetchData() {
            setLoading(true)
            // Fetch Document
            const { data: docData } = await supabase
                .from('documents')
                .select('*')
                .eq('id', id)
                .single()

            if (docData) setDocument(docData)

            // Fetch Items
            const { data: itemsData } = await supabase
                .from('compliance_items')
                .select('*')
                .eq('document_id', id)
                .order('item_index', { ascending: true })

            if (itemsData) setItems(itemsData)

            setLoading(false)
        }
        if (id) fetchData()
    }, [id])

    if (loading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>
    if (!document) return <div className="p-8">Regulation not found.</div>

    return (
        <div className="space-y-6 h-[calc(100vh-100px)] flex flex-col">
            <div>
                <h1 className="text-2xl font-bold tracking-tight">{document.filename}</h1>
                <div className="flex gap-2 mt-2">
                    <Badge variant="outline">{document.language}</Badge>
                    <Badge variant="secondary">{document.page_count} Pages</Badge>
                    <span className="text-sm text-muted-foreground self-center">
                        {items.length} Requirements extracted
                    </span>
                </div>
            </div>

            <Card className="flex-1 overflow-hidden flex flex-col">
                <CardHeader className="bg-muted/30 pb-4">
                    <CardTitle className="text-lg">Compliance Requirements</CardTitle>
                </CardHeader>
                <CardContent className="p-0 flex-1 relative">
                    <ScrollArea className="h-full p-4">
                        <div className="space-y-4">
                            {items.map((item) => (
                                <div key={item.id} className="p-4 border rounded-lg bg-card hover:bg-muted/20 transition-colors">
                                    <div className="flex justify-between items-start gap-4 mb-2">
                                        <Badge variant="outline" className="font-mono text-xs">
                                            {item.section || `Item ${item.item_index}`}
                                        </Badge>
                                    </div>
                                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                                        {item.item_text}
                                    </p>
                                    {item.item_json?.recommendation && (
                                        <div className="mt-2 text-xs text-muted-foreground bg-muted p-2 rounded">
                                            <strong>Recommendation:</strong> {item.item_json.recommendation}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </ScrollArea>
                </CardContent>
            </Card>
        </div>
    )
}
