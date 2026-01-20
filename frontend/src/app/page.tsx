
"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { supabase } from "@/lib/supabase"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { PlusCircle, Activity, Github, Play, Clock } from "lucide-react"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"

export default function DashboardPage() {
    const [repositories, setRepositories] = useState<any[]>([])
    const [recentScans, setRecentScans] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    // New Repo Dialog State
    const [isDialogOpen, setIsDialogOpen] = useState(false)
    const [newRepoUrl, setNewRepoUrl] = useState("")
    const [newRepoName, setNewRepoName] = useState("")
    const [addingRepo, setAddingRepo] = useState(false)

    useEffect(() => {
        fetchDashboardData()

        // Realtime subscription for scans
        const channel = supabase
            .channel('dashboard-updates')
            .on('postgres_changes', { event: '*', schema: 'public', table: 'scans' },
                () => fetchScansOnly()
            )
            .subscribe()

        return () => {
            supabase.removeChannel(channel)
        }
    }, [])

    async function fetchDashboardData() {
        setLoading(true)
        await Promise.all([fetchRepositories(), fetchScansOnly()])
        setLoading(false)
    }

    async function fetchRepositories() {
        const { data } = await supabase.from('repositories').select('*').order('created_at', { ascending: false })
        if (data) setRepositories(data)
    }

    async function fetchScansOnly() {
        // Fetch scans with their results to calculate score
        const { data, error } = await supabase
            .from('scans')
            .select(`
                *,
                scan_results (status)
            `)
            .order('created_at', { ascending: false })
            .limit(10)

        if (data) {
            const scansWithScore = data.map((scan: any) => {
                const results = scan.scan_results || []
                const total = results.length
                const passed = results.filter((r: any) => r.status === 'PASS').length
                const score = total > 0 ? Math.round((passed / total) * 100) : 0
                return { ...scan, score, total, passed }
            })
            setRecentScans(scansWithScore)
        }
    }

    const handleAddRepo = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!newRepoUrl || !newRepoName) return

        setAddingRepo(true)
        const { error } = await supabase.from('repositories').insert({
            name: newRepoName,
            url: newRepoUrl,
        })

        if (!error) {
            setIsDialogOpen(false)
            setNewRepoUrl("")
            setNewRepoName("")
            fetchRepositories()
        } else {
            console.error(error)
            alert('Failed to add repository: ' + error.message)
        }
        setAddingRepo(false)
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                    <p className="text-muted-foreground">Manage your repositories and compliance audits.</p>
                </div>
                <Button asChild>
                    <Link href="/new">
                        <PlusCircle className="mr-2 h-4 w-4" />
                        New Audit
                    </Link>
                </Button>
            </div>

            {/* Repositories Section */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold flex items-center gap-2">
                        <Github className="w-5 h-5" /> My Repositories
                    </h2>
                    <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                        <DialogTrigger asChild>
                            <Button variant="outline" size="sm">Add Repository</Button>
                        </DialogTrigger>
                        <DialogContent>
                            <DialogHeader>
                                <DialogTitle>Add Repository</DialogTitle>
                                <DialogDescription>
                                    Enter the details of the Git repository you want to track.
                                </DialogDescription>
                            </DialogHeader>
                            <form onSubmit={handleAddRepo} className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="name">Repository Name</Label>
                                    <Input
                                        id="name"
                                        placeholder="e.g. backend-api"
                                        value={newRepoName}
                                        onChange={e => setNewRepoName(e.target.value)}
                                        required
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="url">Repository URL</Label>
                                    <Input
                                        id="url"
                                        placeholder="https://github.com/..."
                                        value={newRepoUrl}
                                        onChange={e => setNewRepoUrl(e.target.value)}
                                        required
                                    />
                                </div>
                                <DialogFooter>
                                    <Button type="submit" disabled={addingRepo}>
                                        {addingRepo ? 'Adding...' : 'Add Repository'}
                                    </Button>
                                </DialogFooter>
                            </form>
                        </DialogContent>
                    </Dialog>
                </div>

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {repositories.length === 0 ? (
                        <div className="col-span-full text-center p-8 border border-dashed rounded-lg text-muted-foreground bg-muted/20">
                            No repositories added yet. Click "Add Repository" to get started.
                        </div>
                    ) : (
                        repositories.map(repo => (
                            <Card key={repo.id} className="hover:shadow-md transition-shadow">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-base font-medium truncate" title={repo.name}>
                                        {repo.name}
                                    </CardTitle>
                                    <CardDescription className="truncate text-xs" title={repo.url}>
                                        {repo.url}
                                    </CardDescription>
                                </CardHeader>
                                <CardFooter className="pt-2">
                                    <Button size="sm" className="w-full" asChild>
                                        <Link href={`/new?repo=${encodeURIComponent(repo.url)}`}>
                                            <Play className="w-3 h-3 mr-2" /> Start Scan
                                        </Link>
                                    </Button>
                                </CardFooter>
                            </Card>
                        ))
                    )}
                </div>
            </div>

            {/* Scan History Section */}
            <div className="space-y-4">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                    <Activity className="w-5 h-5" /> Recent Scans
                </h2>
                <Card>
                    <CardContent className="p-0">
                        {recentScans.length === 0 ? (
                            <div className="p-8 text-center text-muted-foreground">
                                No scans performed yet.
                            </div>
                        ) : (
                            <div className="divide-y">
                                {recentScans.map((scan) => (
                                    <div key={scan.id} className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors">
                                        <div className="space-y-1">
                                            <div className="flex items-center gap-2">
                                                <span className="font-medium text-sm">{scan.repo_url}</span>
                                                <Badge variant={
                                                    scan.status === 'COMPLETED' ? 'default' :
                                                        scan.status === 'PROCESSING' ? 'secondary' : 'outline'
                                                } className={
                                                    scan.status === 'COMPLETED' ? 'bg-green-500 hover:bg-green-600' :
                                                        scan.status === 'PROCESSING' ? 'bg-yellow-500 hover:bg-yellow-600 text-white' : ''
                                                }>
                                                    {scan.status}
                                                </Badge>
                                                {scan.status === 'COMPLETED' && (
                                                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${scan.score === 100
                                                            ? "text-green-700 bg-green-100 border-green-200"
                                                            : "text-red-700 bg-red-100 border-red-200"
                                                        }`}>
                                                        Score: {scan.score}% ({scan.passed}/{scan.total})
                                                    </span>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                <Clock className="w-3 h-3" />
                                                {new Date(scan.created_at).toLocaleString()}
                                            </div>
                                        </div>
                                        <Button variant="ghost" size="sm" asChild>
                                            <Link href={`/scans/${scan.id}`}>View Report</Link>
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
