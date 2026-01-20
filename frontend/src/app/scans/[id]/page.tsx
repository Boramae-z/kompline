
"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { supabase } from "@/lib/supabase"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Loader2, CheckCircle2, XCircle, AlertCircle } from "lucide-react"

export default function ScanResultPage() {
    const params = useParams()
    const id = params.id as string

    const [scan, setScan] = useState<any>(null)
    const [results, setResults] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    // Polling / Realtime subscription
    useEffect(() => {
        if (!id) return

        const fetchScan = async () => {
            const { data } = await supabase.from('scans').select('*').eq('id', id).single()
            if (data) setScan(data)
        }

        const fetchResults = async () => {
            // Join with compliance_items to get text
            const { data } = await supabase
                .from('scan_results')
                .select(`
            *,
            compliance_items (
                item_text,
                section
            )
        `)
                .eq('scan_id', id)

            if (data) {
                setResults(data)
            }
            setLoading(false)
        }

        fetchScan()
        fetchResults()

        // Realtime subscription
        const channel = supabase
            .channel('scan-updates')
            .on('postgres_changes', { event: '*', schema: 'public', table: 'scans', filter: `id=eq.${id}` },
                (payload) => setScan(payload.new)
            )
            .on('postgres_changes', { event: '*', schema: 'public', table: 'scan_results', filter: `scan_id=eq.${id}` },
                () => fetchResults() // Refetch all to keep it simple
            )
            .subscribe()

        return () => {
            supabase.removeChannel(channel)
        }
    }, [id])

    if (loading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>
    if (!scan) return <div className="p-8">Scan not found.</div>

    const total = results.length
    const completed = results.filter(r => r.status !== 'PENDING').length
    const passed = results.filter(r => r.status === 'PASS').length
    const progress = total > 0 ? (completed / total) * 100 : 0

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold font-mono">{scan.repo_url}</h1>
                    <p className="text-muted-foreground flex items-center gap-2">
                        Status: <Badge variant={scan.status === 'COMPLETED' ? 'default' : 'secondary'}>{scan.status}</Badge>
                    </p>
                </div>
                {scan.status === 'COMPLETED' && (
                    <div className="flex gap-2">
                        <div className="text-right">
                            <p className="text-sm font-medium">Compliance Score</p>
                            <p className="text-2xl font-bold text-green-600">
                                {total > 0 ? Math.round((passed / total) * 100) : 0}%
                            </p>
                        </div>
                    </div>
                )}
            </div>

            <Card>
                <CardContent className="pt-6">
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                            <span>Progress</span>
                            <span>{completed} / {total} items checked</span>
                        </div>
                        <Progress value={progress} className="w-full" />
                    </div>
                </CardContent>
            </Card>

            <div className="grid gap-4">
                <h2 className="text-xl font-semibold">Validation Results</h2>
                {results.length === 0 ? (
                    <p className="text-muted-foreground">Initializing agents...</p>
                ) : (
                    results.map((res) => (
                        <Card key={res.id} className={res.status === 'FAIL' ? 'border-red-200 bg-red-50/10' : ''}>
                            <CardHeader className="pb-2">
                                <div className="flex items-start justify-between gap-4">
                                    <div className="space-y-1">
                                        <CardTitle className="text-base font-medium leading-relaxed">
                                            {res.compliance_items?.item_text || "Unknown Requirement"}
                                        </CardTitle>
                                        <p className="text-xs text-muted-foreground">
                                            Section: {res.compliance_items?.section || 'N/A'}
                                        </p>
                                    </div>
                                    <div>
                                        {res.status === 'PASS' && <Badge className="bg-green-500 hover:bg-green-600"><CheckCircle2 className="w-3 h-3 mr-1" /> PASS</Badge>}
                                        {res.status === 'FAIL' && <Badge variant="destructive"><XCircle className="w-3 h-3 mr-1" /> FAIL</Badge>}
                                        {res.status === 'PENDING' && <Badge variant="outline" className="animate-pulse"><Loader2 className="w-3 h-3 mr-1 animate-spin" /> CHECKING</Badge>}
                                    </div>
                                </div>
                            </CardHeader>
                            {res.status !== 'PENDING' && res.reasoning && (
                                <CardContent>
                                    <div className="text-sm bg-muted/50 p-3 rounded-md">
                                        <span className="font-semibold block mb-1">Agent Reasoning:</span>
                                        {res.reasoning}
                                    </div>
                                </CardContent>
                            )}
                        </Card>
                    ))
                )}
            </div>
        </div>
    )
}
