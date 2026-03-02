import { useQuery } from "@tanstack/react-query"
import { Download, Film, Trophy } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"
import type { Recording } from "@/lib/api"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

interface RunRecordingsSectionProps {
  runId: string
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function RunRecordingsSection({ runId }: RunRecordingsSectionProps) {
  const { data: recordings, isLoading } = useQuery({
    queryKey: ["runs", runId, "recordings"],
    queryFn: () => api.runs.recordings(runId),
  })

  if (isLoading || !recordings || recordings.length === 0) return null

  const hasRewardData = recordings.some((r: Recording) => r.reward !== null)
  const bestReward = hasRewardData
    ? Math.max(...recordings.filter((r: Recording) => r.reward !== null).map((r: Recording) => r.reward!))
    : null

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm flex items-center gap-2">
              <Film className="size-4" />
              Episode Recordings
            </CardTitle>
            <CardDescription className="text-xs mt-1">
              {recordings.length} episode{recordings.length !== 1 ? "s" : ""} recorded
              {hasRewardData ? " — sorted by reward" : ""}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">#</TableHead>
                {hasRewardData && <TableHead className="w-24">Reward</TableHead>}
                {hasRewardData && <TableHead className="w-24">Length</TableHead>}
                {hasRewardData && <TableHead className="w-24">Step</TableHead>}
                <TableHead className="w-20">Size</TableHead>
                <TableHead className="w-10" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {recordings.map((rec: Recording, idx: number) => {
                const isBest = hasRewardData && rec.reward !== null && rec.reward === bestReward
                return (
                  <TableRow key={rec.filename}>
                    <TableCell className="font-mono text-xs">
                      {rec.episode_seq ?? idx}
                    </TableCell>
                    {hasRewardData && (
                      <TableCell>
                        <span className="flex items-center gap-1">
                          {rec.reward !== null ? (
                            <>
                              <span className="font-mono text-sm">{rec.reward.toFixed(1)}</span>
                              {isBest && idx === 0 && (
                                <Badge variant="default" className="text-[10px] px-1 py-0 h-4">
                                  <Trophy className="size-2.5 mr-0.5" />
                                  Best
                                </Badge>
                              )}
                            </>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </span>
                      </TableCell>
                    )}
                    {hasRewardData && (
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {rec.length != null ? `${rec.length} steps` : "—"}
                      </TableCell>
                    )}
                    {hasRewardData && (
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {rec.step != null ? rec.step.toLocaleString() : "—"}
                      </TableCell>
                    )}
                    <TableCell className="text-xs text-muted-foreground">
                      {formatBytes(rec.size)}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="icon" className="size-7" asChild>
                        <a
                          href={`${API_BASE}/api/runs/${runId}/recordings/${rec.filename}`}
                          download={rec.filename}
                        >
                          <Download className="size-3.5" />
                        </a>
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
