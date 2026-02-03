import { Copy, Play, Square, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { PageHeader, PageTitle, PageDescription, PageActions } from "@/components/ui/page"
import { StatusBadge } from "@/components/shared"
import { useStopRun, useResumeRun } from "@/hooks"
import { DeleteRunDialog } from "./delete-run-dialog"
import type { Run } from "@/lib/schemas"

interface RunDetailsHeaderProps {
    run: Run
}

export function RunDetailsHeader({ run }: RunDetailsHeaderProps) {
    const [showDelete, setShowDelete] = useState(false)
    const stopRun = useStopRun()
    const resumeRun = useResumeRun()
    const isRunning = run.status === "running"

    const copyId = () => {
        navigator.clipboard.writeText(run.id)
        toast.success("Run ID copied")
    }

    return (
        <>
            <PageHeader className="flex-row items-start justify-between gap-4">
                <div>
                    <div className="flex items-center gap-3">
                        <PageTitle>{run.rom}</PageTitle>
                        <StatusBadge status={run.status} />
                        <Badge variant="outline">{run.algorithm}</Badge>
                    </div>
                    <PageDescription className="flex items-center gap-4 mt-1">
                        <span>{run.state}</span>
                        <button
                            onClick={copyId}
                            className="flex items-center gap-1 hover:text-foreground transition-colors"
                            title="Copy Run ID"
                        >
                            <Copy className="size-3" />
                            <span className="font-mono text-xs text-muted-foreground">{run.id.slice(0, 8)}...</span>
                        </button>
                    </PageDescription>
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
