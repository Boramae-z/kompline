
"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { supabase } from "@/lib/supabase"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Loader2, CheckCircle2, XCircle, AlertCircle, FileText, Printer } from "lucide-react"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from "@/components/ui/button"

export default function ScanResultPage() {
    const params = useParams()
    const id = params.id as string

    const [scan, setScan] = useState<any>(null)
    const [results, setResults] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    // ... (rest of the state and effects remain same, skipping to render)

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
                <div className="min-w-0 flex-1">
                    <h1 className="text-2xl font-bold font-mono break-all pr-4">{scan.repo_url}</h1>
                    <p className="text-muted-foreground flex items-center gap-2">
                        Status: <Badge variant={scan.status === 'COMPLETED' ? 'default' : 'secondary'}>{scan.status}</Badge>
                    </p>
                </div>
                <div className="flex items-center gap-4">
                    {scan.status === 'COMPLETED' && (
                        <div className="text-right">
                            <p className="text-sm font-medium">Compliance Score</p>
                            <p className={`text-2xl font-bold ${(total > 0 ? Math.round((passed / total) * 100) : 0) === 100
                                ? "text-green-600"
                                : "text-red-500"
                                }`}>
                                {total > 0 ? Math.round((passed / total) * 100) : 0}%
                            </p>
                        </div>
                    )}
                    <Button variant="outline" size="sm" onClick={() => window.print()}>
                        <Printer className="w-4 h-4 mr-2" />
                        Export PDF
                    </Button>
                </div>
            </div>

            <Card className="print:hidden">
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
                <h2 className="text-xl font-semibold print:hidden">Validation Results</h2>
                {results.length === 0 ? (
                    <p className="text-muted-foreground">Initializing agents...</p>
                ) : (
                    results.map((res) => (
                        <Card key={res.id} className={`${res.status === 'FAIL' ? 'border-red-200 bg-red-50/10' : ''} break-inside-avoid`}>
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
                            {res.status !== 'PENDING' && (
                                <CardContent className="space-y-4">
                                    {res.reasoning && (
                                        <div className="text-sm bg-muted/50 p-3 rounded-md">
                                            <span className="font-semibold block mb-1">Agent Reasoning:</span>
                                            {res.reasoning}
                                        </div>
                                    )}
                                    {res.evidence && (
                                        <div className="text-sm bg-muted/40 border p-3 rounded-md w-full max-w-full overflow-hidden">
                                            <span className="font-semibold block mb-2 flex items-center gap-2">
                                                <span>🔍 Evidence / Code Snippet:</span>
                                            </span>
                                            <pre className="text-xs w-full max-w-full whitespace-pre-wrap break-all bg-stone-900 text-stone-50 p-3 border border-stone-800 rounded font-mono">
                                                {res.evidence}
                                            </pre>
                                        </div>
                                    )}
                                </CardContent>
                            )}
                        </Card>
                    ))
                )}
            </div>

            {/* Final Report Section */}
            {scan.report_markdown && (
                <Card className="mt-8 border-primary/20 shadow-lg break-before-page">
                    <CardHeader className="bg-primary/5">
                        <CardTitle className="flex items-center gap-2">
                            <FileText className="w-5 h-5" /> Final Report
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="prose dark:prose-invert max-w-none p-6">
                        {/* Assuming report_url actually contains the markdown content for this demo, 
                            or we fetch it. For simplicity if it's text, display it. 
                            If it's a URL, we might need to fetch it or link to it. 
                            Let's assume for the MVP the agent writes the summary into a 'report_markdown' 
                            column or we display what's there. 
                            Wait, the schema says report_url. Let's assume we want to display 'report_markdown' if we added it,
                            or just handle text in report_url if the user meant that.
                            The user said "scans 테이블의 report_markdown도 보여줘". 
                            So I need to make sure I select it.
                        */}
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                                h1: ({ node, ...props }) => <h1 className="text-2xl font-bold mt-6 mb-4" {...props} />,
                                h2: ({ node, ...props }) => <h2 className="text-xl font-semibold mt-5 mb-3" {...props} />,
                                h3: ({ node, ...props }) => <h3 className="text-lg font-medium mt-4 mb-2" {...props} />,
                                ul: ({ node, ...props }) => <ul className="list-disc pl-5 my-2" {...props} />,
                                ol: ({ node, ...props }) => <ol className="list-decimal pl-5 my-2" {...props} />,
                                li: ({ node, ...props }) => <li className="mb-1" {...props} />,
                                code: ({ node, inline, className, children, ...props }: any) => {
                                    return inline ? (
                                        <code className="bg-muted px-1 py-0.5 rounded text-sm font-mono" {...props}>
                                            {children}
                                        </code>
                                    ) : (
                                        <pre className="bg-stone-900 text-stone-50 p-4 rounded-lg overflow-x-auto my-4 text-sm font-mono border border-stone-800">
                                            <code {...props}>{children}</code>
                                        </pre>
                                    )
                                },
                                table: ({ node, ...props }) => <div className="overflow-x-auto my-4"><table className="w-full border-collapse text-sm" {...props} /></div>,
                                th: ({ node, ...props }) => <th className="border p-2 bg-muted font-semibold text-left" {...props} />,
                                td: ({ node, ...props }) => <td className="border p-2" {...props} />,
                                blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-primary/30 pl-4 italic text-muted-foreground my-4" {...props} />,
                            }}
                        >
                            {scan.report_markdown || "No report content generated."}
                        </ReactMarkdown>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
