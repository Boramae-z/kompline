
"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabase"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Loader2 } from "lucide-react"


import { useSearchParams } from "next/navigation"

export default function NewScanPage() {
    const router = useRouter()
    const searchParams = useSearchParams()

    const [loading, setLoading] = useState(false)
    const [repoUrl, setRepoUrl] = useState("")
    const [documents, setDocuments] = useState<any[]>([])
    const [selectedDocs, setSelectedDocs] = useState<number[]>([])

    useEffect(() => {
        const repoParam = searchParams.get('repo')
        if (repoParam) {
            setRepoUrl(repoParam)
        }
    }, [searchParams])

    useEffect(() => {
        async function fetchDocuments() {
            const { data, error } = await supabase
                .from('documents')
                .select('id, filename, language, page_count')

            if (error) {
                console.error('Error fetching documents:', error)
            } else {
                setDocuments(data || [])
            }
        }
        fetchDocuments()
    }, [])

    const handleToggleDoc = (docId: number) => {
        setSelectedDocs(prev =>
            prev.includes(docId)
                ? prev.filter(id => id !== docId)
                : [...prev, docId]
        )
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!repoUrl || selectedDocs.length === 0) return

        setLoading(true)
        try {
            // 1. Create Scan
            const { data: scan, error: scanError } = await supabase
                .from('scans')
                .insert({
                    repo_url: repoUrl,
                    status: 'QUEUED'
                })
                .select()
                .single()

            if (scanError) throw scanError

            // 2. Link Documents
            const junctionData = selectedDocs.map(docId => ({
                scan_id: scan.id,
                document_id: docId
            }))

            const { error: junctionError } = await supabase
                .from('scan_documents')
                .insert(junctionData)

            if (junctionError) throw junctionError

            // 3. Trigger Agent Dispatcher (Mocked here by just creating placeholder results if we were doing fully client-side demo, but strictly we just wait for backend)
            // For now, we just redirect.
            router.push(`/scans/${scan.id}`)

        } catch (error) {
            console.error('Error creating scan:', error)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">New Audit</h1>
                <p className="text-muted-foreground">Configure your compliance scan.</p>
            </div>

            <form onSubmit={handleSubmit}>
                <Card>
                    <CardHeader>
                        <CardTitle>Artifact Details</CardTitle>
                        <CardDescription>
                            Provide the location of the codebase or artifact you want to audit.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="repo-url">Repository URL</Label>
                            <Input
                                id="repo-url"
                                placeholder="https://github.com/my-org/my-repo"
                                value={repoUrl}
                                onChange={(e) => setRepoUrl(e.target.value)}
                                required
                            />
                        </div>
                    </CardContent>
                </Card>

                <Card className="mt-6">
                    <CardHeader>
                        <CardTitle>Select Regulations</CardTitle>
                        <CardDescription>
                            Choose which compliance documents to check against.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {documents.length === 0 ? (
                            <div className="text-center py-4 text-muted-foreground">
                                No regulations found in database.
                            </div>
                        ) : (
                            <div className="grid gap-4">
                                {documents.map((doc) => (
                                    <div key={doc.id} className="flex items-start space-x-3 space-y-0">
                                        <Checkbox
                                            id={`doc-${doc.id}`}
                                            checked={selectedDocs.includes(doc.id)}
                                            onCheckedChange={() => handleToggleDoc(doc.id)}
                                        />
                                        <div className="grid gap-1.5 leading-none">
                                            <label
                                                htmlFor={`doc-${doc.id}`}
                                                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                            >
                                                {doc.filename}
                                            </label>
                                            <p className="text-xs text-muted-foreground">
                                                {doc.language} • {doc.page_count} pages
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                    <CardFooter className="flex justify-end">
                        <Button type="submit" disabled={loading || !repoUrl || selectedDocs.length === 0}>
                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Start Audit
                        </Button>
                    </CardFooter>
                </Card>
            </form>
        </div>
    )
}
