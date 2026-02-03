import { Copy, Play, Square, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { PageHeader, PageTitle, PageDescription, PageActions } from "@/components/ui/page"
import { StatusBadge } from "@/components/shared"
import { useStopRun, useResumeRun, useRoms, useGameMetadata } from "@/hooks"
import { DeleteRunDialog } from "./delete-run-dialog"
import type { Run } from "@/lib/schemas"

interface RunDetailsHeaderProps {
    run: Run
}

export function RunDetailsHeader({ run }: RunDetailsHeaderProps) {
    const [showDelete, setShowDelete] = useState(false)
    const stopRun = useStopRun()
    const resumeRun = useResumeRun()

    // Fetch Metadata
    const { data: roms = [] } = useRoms()
    // Finding the ROM object to get the System ID
    // Run object has 'rom', which is the Game ID (e.g., 'SuperMarioWorld-Snes-v0' or similar)
    // Actually run.rom seems to be the ID.
    const rom = roms.find(r => r.id === run.rom)
    const { data: metadata } = useGameMetadata(
        rom?.system ?? null,
        rom?.id ?? null
    )

    const isRunning = run.status === "running"

    const copyId = () => {
        navigator.clipboard.writeText(run.id)
        toast.success("Run ID copied")
    }

    return (
        <>
            <PageHeader className="flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-6">
                    {metadata?.cover_url && (
                        <div className="hidden sm:block shrink-0 relative hover:scale-105 transition-transform duration-200">
                            <img
                                src={metadata.cover_url.replace("t_thumb", "t_cover_big")}
                                alt={metadata.name}
                                className="w-16 h-24 object-cover rounded shadow-sm"
                            />
                        </div>
                    )}

                    <div>
                        <div className="flex items-center gap-3">
                            <PageTitle>{metadata?.name || run.rom}</PageTitle>
                            <StatusBadge status={run.status} />
                            <Badge variant="outline">{run.algorithm}</Badge>
                        </div>
                        <PageDescription className="flex items-center gap-4 mt-1">
                            {/* If we have nicer system name from metadata, maybe use it? But keeping state is good */}
                            <span>{rom ? `${rom.system} • ` : ''}{run.state}</span>
                            <button
                                onClick={copyId}
                                className="flex items-center gap-1 hover:text-foreground transition-colors"
                                title="Copy Run ID"
                            >
                                <Copy className="size-3" />
                                <span className="font-mono text-xs text-muted-foreground">{run.id.slice(0, 8)}...</span>
                            </button>
                        </PageDescription>
                        {metadata?.genres && (
                            <div className="flex gap-2 mt-2">
                                {metadata.genres.slice(0, 3).map(g => (
                                    <span key={g} className="text-[10px] text-muted-foreground px-1.5 py-0.5 border rounded-full bg-background/50">
                                        {g}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <PageActions>
                    {run.status === "stopped" && (
                        <Button
                            variant="outline"
                            onClick={() => resumeRun.mutate(run.id)}
                            disabled={resumeRun.isPending}
                        >
                            <Play className="size-4 mr-2" />
                            Resume
                        </Button>
                    )}

                    {isRunning && (
                        <Button
                            variant="outline"
                            onClick={() => stopRun.mutate(run.id)}
                            disabled={stopRun.isPending}
                        >
                            <Square className="size-4 mr-2" />
                            Stop
                        </Button>
                    )}

                    <Button variant="destructive" onClick={() => setShowDelete(true)}>
                        <Trash2 className="size-4 mr-2" />
                        Delete
                    </Button>
                </PageActions>
            </PageHeader>

            <DeleteRunDialog
                runId={run.id}
                open={showDelete}
                onOpenChange={setShowDelete}
            />
        </>
    )
}
