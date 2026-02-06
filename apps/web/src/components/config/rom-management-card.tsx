import { useState, useEffect, useRef, type ReactNode } from "react"
import { FolderInput, RefreshCw, Database, CheckCircle, AlertCircle, Clock, FolderOpen, Image, Terminal, Loader2, ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { DirectoryPickerDialog } from "@/components/ui/directory-picker-dialog"
import { useScanRoms, useSyncStatus, useSyncAll, useSyncThumbnails } from "@/hooks"
import { LabelWithTooltip } from "./common"
import type { ConfigUpdate } from "@/lib/schemas"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"

type ImportStage = "idle" | "importing" | "scanning" | "syncing" | "complete" | "error"

interface LogEntry {
  timestamp: Date
  message: string
  type: "info" | "success" | "error" | "progress"
}

interface RomManagementCardProps {
  formData: ConfigUpdate
  onChange: (field: keyof ConfigUpdate, value: ConfigUpdate[keyof ConfigUpdate]) => void
}

export function RomManagementCard({ formData, onChange }: RomManagementCardProps) {
  const [pickerOpen, setPickerOpen] = useState(false)
  const [importStage, setImportStage] = useState<ImportStage>("idle")
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [showLogs, setShowLogs] = useState(false)
  const [lastSyncCurrent, setLastSyncCurrent] = useState<string | null>(null)
  const [currentProgress, setCurrentProgress] = useState<{ current: number; total: number } | null>(null)
  const [includeUnmatchedConnectors, setIncludeUnmatchedConnectors] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  const scanRoms = useScanRoms()
  const { data: syncStatus, refetch: refetchSyncStatus } = useSyncStatus()
  const syncAll = useSyncAll()
  const syncThumbnails = useSyncThumbnails()

  const addLog = (message: string, type: LogEntry["type"] = "info") => {
    setLogs(prev => [...prev, { timestamp: new Date(), message, type }])
  }


  // Track sync progress in logs (legitimate async state machine reacting to external sync status)
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (importStage === "syncing" && syncStatus) {
      // Only log when current changes
      if (syncStatus.current && syncStatus.current !== lastSyncCurrent) {
        setLastSyncCurrent(syncStatus.current)
        addLog(`Syncing: ${syncStatus.current}`, "progress")
      }
      // Detect completion
      if (!syncStatus.is_syncing && lastSyncCurrent !== null) {
        addLog(`Sync complete: ${syncStatus.synced} ROMs synced, ${syncStatus.failed} failed`, "success")
        setImportStage("complete")
        setLastSyncCurrent(null)
      }
    }
  }, [syncStatus, importStage, lastSyncCurrent])
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleImport = () => {
    if (!formData.roms_path) return

    setLogs([])
    setShowLogs(true)
    setImportStage("importing")
    setLastSyncCurrent(null)
    setCurrentProgress(null)
    addLog(`Starting import from: ${formData.roms_path}`, "info")

    // Cancel any existing stream
    abortControllerRef.current?.abort()

    abortControllerRef.current = api.roms.importStream(formData.roms_path, {
      onStart: (phase, message) => {
        addLog(message, "info")
        if (phase === "scan_connectors" || phase === "scan_folder") {
          setImportStage("scanning")
        }
      },
      onProgress: (_phase, current, total, message) => {
        setCurrentProgress({ current, total })
        // Only log every 100 items to avoid spam
        if (current % 100 === 0 || current === total) {
          addLog(message, "progress")
        }
      },
      onComplete: (phase, result) => {
        setCurrentProgress(null)
        if (phase === "import") {
          addLog(`Imported ${result.imported} ROM(s) into stable-retro`, "success")
        } else if (phase === "scan_connectors") {
          addLog(`Found ${result.count} connectors`, "success")
        } else if (phase === "scan_folder") {
          addLog(`Found ${result.count} ROM files`, "success")
        } else if (phase === "register") {
          addLog(`${result.queued_for_sync} ROM(s) queued for sync`, "info")
        }
      },
      onDone: (result) => {
        if (result.syncing) {
          setImportStage("syncing")
          addLog("Starting metadata sync in background...", "info")
        } else {
          setImportStage("complete")
          addLog("Import complete!", "success")
        }
        // Refresh sync status
        refetchSyncStatus()
      },
      onError: (message) => {
        setImportStage("error")
        addLog(`Import failed: ${message}`, "error")
      },
    })
  }

  const handleScan = () => {
    setLogs([])
    setShowLogs(true)
    setImportStage("scanning")
    setLastSyncCurrent(null)
    addLog("Scanning library...", "info")

    scanRoms.mutate(undefined, {
      onSuccess: (result) => {
        addLog(`Found ${result.queued_for_sync} ROM(s) to sync`, "success")
        if (result.syncing) {
          setImportStage("syncing")
          addLog("Starting metadata sync...", "info")
        } else {
          setImportStage("complete")
          addLog("Scan complete!", "success")
        }
      },
      onError: (error) => {
        setImportStage("error")
        addLog(`Scan failed: ${error.message}`, "error")
      },
    })
  }

  const handleSyncAll = () => {
    setLogs([])
    setShowLogs(true)
    setImportStage("syncing")
    setLastSyncCurrent(null)
    addLog(includeUnmatchedConnectors
      ? "Starting metadata sync (including unmatched connectors)..."
      : "Starting metadata sync for ROMs...",
      "info"
    )
    syncAll.mutate(includeUnmatchedConnectors)
  }

  const syncProgress = syncStatus && syncStatus.total > 0
    ? Math.round((syncStatus.completed / (syncStatus.pending + syncStatus.completed)) * 100) || 0
    : 0

  // Calculate scanning progress
  const scanProgress = currentProgress
    ? Math.round((currentProgress.current / currentProgress.total) * 100)
    : 0

  const isWorking = importStage === "importing" || importStage === "scanning" || importStage === "syncing"

  const getStageLabel = () => {
    switch (importStage) {
      case "importing": return "Importing ROMs..."
      case "scanning": return "Scanning library..."
      case "syncing": return "Syncing metadata..."
      case "complete": return "Complete"
      case "error": return "Error"
      default: return null
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-1">
        <h3 className="text-lg font-medium mb-1">ROM Management</h3>
        <p className="text-sm text-muted-foreground">Import and sync your game library.</p>
      </div>
      <Card className="lg:col-span-2">
        <CardContent className="space-y-6 pt-6">
          {/* ROMs Path Input */}
          <div className="space-y-2">
            <LabelWithTooltip tooltip="Directory containing ROM files to import into stable-retro.">
              ROMs Directory
            </LabelWithTooltip>
            <div className="flex gap-2">
              <div className="flex-1 flex gap-1">
                <Input
                  value={formData.roms_path || ""}
                  onChange={(e) => onChange("roms_path", e.target.value)}
                  placeholder="/home/user/roms"
                  className="font-mono text-sm"
                  disabled={isWorking}
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setPickerOpen(true)}
                  title="Browse directories"
                  disabled={isWorking}
                >
                  <FolderOpen className="size-4" />
                </Button>
              </div>
              <Button
                onClick={handleImport}
                disabled={!formData.roms_path || isWorking}
                variant="secondary"
              >
                {importStage === "importing" ? (
                  <Loader2 className="size-4 mr-2 animate-spin" />
                ) : (
                  <FolderInput className="size-4 mr-2" />
                )}
                {importStage === "importing" ? "Importing..." : "Import"}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Imports ROMs from this directory into stable-retro and syncs metadata.
            </p>
          </div>

          <DirectoryPickerDialog
            open={pickerOpen}
            onOpenChange={setPickerOpen}
            onSelect={(path) => onChange("roms_path", path)}
            title="Select ROMs Directory"
            description="Browse to the directory containing your ROM files."
            initialPath={formData.roms_path || undefined}
          />

          {/* Import/Sync Progress Panel */}
          {(isWorking || logs.length > 0) && (
            <div className="border overflow-hidden">
              {/* Progress Header */}
              <div
                className={cn(
                  "flex items-center justify-between p-3 cursor-pointer",
                  isWorking ? "bg-primary/10" : importStage === "error" ? "bg-destructive/10" : "bg-muted/50"
                )}
                onClick={() => setShowLogs(!showLogs)}
              >
                <div className="flex items-center gap-3">
                  {isWorking ? (
                    <Loader2 className="size-4 animate-spin text-primary" />
                  ) : importStage === "error" ? (
                    <AlertCircle className="size-4 text-destructive" />
                  ) : importStage === "complete" ? (
                    <CheckCircle className="size-4 text-chart-1" />
                  ) : (
                    <Terminal className="size-4" />
                  )}
                  <span className="text-sm font-medium">
                    {getStageLabel() || "Activity Log"}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  {isWorking && importStage === "syncing" && syncStatus && (
                    <span className="text-xs text-muted-foreground">
                      {syncStatus.completed}/{syncStatus.pending + syncStatus.completed}
                    </span>
                  )}
                  {isWorking && (importStage === "scanning" || importStage === "importing") && currentProgress && (
                    <span className="text-xs text-muted-foreground">
                      {currentProgress.current}/{currentProgress.total}
                    </span>
                  )}
                  {showLogs ? (
                    <ChevronUp className="size-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="size-4 text-muted-foreground" />
                  )}
                </div>
              </div>

              {/* Progress Bar */}
              {isWorking && (importStage === "syncing" || importStage === "scanning" || importStage === "importing") && (
                <Progress
                  value={importStage === "syncing" ? syncProgress : scanProgress}
                  className="h-1"
                />
              )}

              {/* Log Output */}
              {showLogs && (
                <div className="font-mono text-xs p-3 max-h-48 overflow-y-auto text-chart-2" style={{ backgroundColor: "rgba(0,0,0,0.9)" }}>
                  {logs.map((log, i) => (
                    <div
                      key={i}
                      className={cn(
                        "py-0.5",
                        log.type === "error" && "text-destructive",
                        log.type === "success" && "text-chart-2",
                        log.type === "progress" && "text-chart-4",
                        log.type === "info" && "text-muted-foreground"
                      )}
                    >
                      <span className="text-muted-foreground/60">
                        [{log.timestamp.toLocaleTimeString()}]
                      </span>{" "}
                      {log.message}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Sync Status */}
          {syncStatus && syncStatus.total > 0 && !isWorking && (
            <div className="space-y-4 p-4 bg-muted/50">
              {/* Header with total */}
              <div className="flex items-center justify-between">
                <span className="font-medium">Library Status</span>
                <span className="text-sm text-muted-foreground">
                  {syncStatus.total} games in database
                </span>
              </div>

              {/* Game Categories */}
              <div className="space-y-2">
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Game Categories
                </div>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div className="p-2 bg-background border">
                    <div className="text-lg font-semibold text-chart-1">{syncStatus.trainable}</div>
                    <div className="text-xs text-muted-foreground">Trainable</div>
                  </div>
                  <div className="p-2 bg-background border">
                    <div className="text-lg font-semibold text-primary">{syncStatus.total_roms}</div>
                    <div className="text-xs text-muted-foreground">With ROM</div>
                  </div>
                  <div className="p-2 bg-background border">
                    <div className="text-lg font-semibold">{syncStatus.total_connectors}</div>
                    <div className="text-xs text-muted-foreground">Connectors</div>
                  </div>
                </div>
              </div>

              {/* Metadata Coverage */}
              <div className="space-y-2">
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Metadata Coverage
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                  <StatRow label="Name" value={syncStatus.with_name} total={syncStatus.total} />
                  <StatRow label="Year" value={syncStatus.with_year} total={syncStatus.total} />
                  <StatRow label="Rating" value={syncStatus.with_rating} total={syncStatus.total} />
                  <StatRow label="Developer" value={syncStatus.with_developer} total={syncStatus.total} />
                  <StatRow label="Summary" value={syncStatus.with_summary} total={syncStatus.total} />
                  <StatRow label="Genres" value={syncStatus.with_genres} total={syncStatus.total} />
                  <StatRow label="Thumbnail" value={syncStatus.with_thumbnail} total={syncStatus.total} icon={<Image className="size-3" />} />
                </div>
              </div>

              {/* Sync Status */}
              {(syncStatus.pending > 0 || syncStatus.failed > 0) && (
                <div className="flex gap-4 pt-2 border-t text-sm">
                  {syncStatus.pending > 0 && (
                    <div className="flex items-center gap-1.5 text-chart-3">
                      <Clock className="size-3.5" />
                      <span>{syncStatus.pending} pending</span>
                    </div>
                  )}
                  {syncStatus.failed > 0 && (
                    <div className="flex items-center gap-1.5 text-destructive">
                      <AlertCircle className="size-3.5" />
                      <span>{syncStatus.failed} failed</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="outline"
              onClick={handleScan}
              disabled={isWorking}
            >
              {importStage === "scanning" ? (
                <Loader2 className="size-4 mr-2 animate-spin" />
              ) : (
                <Database className="size-4 mr-2" />
              )}
              {importStage === "scanning" ? "Scanning..." : "Scan Library"}
            </Button>

            {syncStatus && syncStatus.pending > 0 && (
              <Button
                variant="outline"
                onClick={handleSyncAll}
                disabled={isWorking}
              >
                {importStage === "syncing" ? (
                  <Loader2 className="size-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="size-4 mr-2" />
                )}
                {importStage === "syncing" ? "Syncing..." : `Sync ${syncStatus.pending} Pending`}
              </Button>
            )}

            {syncStatus && syncStatus.missing_thumbnails > 0 && (
              <Button
                variant="outline"
                onClick={() => syncThumbnails.mutate()}
                disabled={isWorking || syncThumbnails.isPending}
              >
                <Image className="size-4 mr-2" />
                {syncThumbnails.isPending ? "Syncing..." : `Fetch ${syncStatus.missing_thumbnails} Thumbnails`}
              </Button>
            )}

            <div className="flex items-center gap-2 ml-auto">
              <Switch
                id="include-unmatched"
                checked={includeUnmatchedConnectors}
                onCheckedChange={setIncludeUnmatchedConnectors}
                disabled={isWorking}
              />
              <Label
                htmlFor="include-unmatched"
                className="text-sm text-muted-foreground cursor-pointer"
              >
                Include connectors without ROMs
              </Label>
            </div>
          </div>

          <p className="text-xs text-muted-foreground">
            <strong>Scan Library</strong> detects ROMs already in stable-retro.{" "}
            <strong>Sync</strong> fetches metadata from IGDB and thumbnails from LibRetro.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

/** Helper component for metadata stat rows */
function StatRow({
  label,
  value,
  total,
  icon,
}: {
  label: string
  value: number
  total: number
  icon?: ReactNode
}) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        {icon || <CheckCircle className="size-3" />}
        <span>{label}</span>
      </div>
      <span className={cn(
        "tabular-nums",
        pct >= 80 && "text-chart-1",
        pct >= 50 && pct < 80 && "text-chart-3",
        pct < 50 && "text-muted-foreground"
      )}>
        {value}/{total}
      </span>
    </div>
  )
}
