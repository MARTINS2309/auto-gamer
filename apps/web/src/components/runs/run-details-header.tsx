import { Copy, Play, Square, Trash2, Gamepad2 } from "lucide-react"
import { toast } from "sonner"
import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
    PageHeader,
    PageHeaderNav,
    PageHeaderItem,
    PageTitle,
    PageDescription,
} from "@/components/ui/page"
import { StatusBadge } from "@/components/shared"
import { useStopRun, useResumeRun, useRoms, useStartPlaySession } from "@/hooks"
import { DeleteRunDialog } from "./delete-run-dialog"
import type { Run } from "@/lib/schemas"

interface RunDetailsHeaderProps {
    run: Run
}

export function RunDetailsHeader({ run }: RunDetailsHeaderProps) {
    const [showDelete, setShowDelete] = useState(false)
    const stopRun = useStopRun()
    const resumeRun = useResumeRun()
    const startPlay = useStartPlaySession()

    // ROM data now includes all metadata directly
    const { data: roms = [] } = useRoms()
    const rom = roms.find(r => r.id === run.rom)

    const displayName = run.game_name ?? rom?.display_name ?? run.rom
    const thumbnailUrl = run.game_thumbnail_url ?? rom?.thumbnail_url
    const genres = rom?.genres ?? []

    const isRunning = run.status === "running"

    const copyId = () => {
        navigator.clipboard.writeText(run.id)
        toast.success("Run ID copied")
    }

    const handlePlay = () => {
        startPlay.mutate({
            romId: run.rom,
            state: run.state
        })
    }

    return (
        <>
            <PageHeader hideOnScroll={false}>
                <PageHeaderNav>
                    <PageHeaderItem>
                        <div className="flex items-center gap-6">
                            {thumbnailUrl && (
                                <div className="hidden sm:block shrink-0 relative hover:scale-105 transition-transform duration-200">
                                    <img
                                        src={thumbnailUrl}
                                        alt={displayName}
                                        className="w-16 h-24 object-cover shadow-sm"
                                    />
                                </div>
                            )}

                            <div>
                                <div className="flex items-center gap-3">
                                    <PageTitle>{displayName}</PageTitle>
                                    <StatusBadge status={run.status} />
                                    {run.agent_name && (
                                        <Badge variant="secondary">{run.agent_name}</Badge>
                                    )}
                                    <Badge variant="outline">{run.algorithm}</Badge>
                                </div>
                                <PageDescription className="flex items-center gap-4 mt-1">
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
                                {genres.length > 0 && (
                                    <div className="flex gap-2 mt-2">
                                        {genres.slice(0, 3).map(g => (
                                            <span key={g} className="text-[10px] text-muted-foreground px-1.5 py-0.5 border bg-background/50">
                                                {g}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </PageHeaderItem>

                    <PageHeaderItem className="ml-auto">
                        <div className="flex items-center gap-2">
                            <Button
                                variant="default"
                                onClick={handlePlay}
                                disabled={startPlay.isPending}
                            >
                                <Gamepad2 className="size-4 mr-2" />
                                {startPlay.isPending ? "Starting..." : "Play"}
                            </Button>

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
                        </div>
                    </PageHeaderItem>
                </PageHeaderNav>
            </PageHeader>

            <DeleteRunDialog
                runId={run.id}
                open={showDelete}
                onOpenChange={setShowDelete}
            />
        </>
    )
}
