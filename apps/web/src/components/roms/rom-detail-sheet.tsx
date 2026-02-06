import { useState } from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Play, Settings2, Gamepad2, RefreshCw, AlertCircle, Wrench } from "lucide-react"
import { Link } from "@tanstack/react-router"
import { StatusBadge } from "@/components/shared"
import { useStartPlaySession, useStopPlaySession, useConfig, useSyncRom } from "@/hooks"
import { PlayFrameViewer } from "./play-frame-viewer"
import type { KeyboardMapping } from "@/lib/schemas"
import {
  RatingDisplay,
  GenreBadges,
  ThemeBadges,
  GameModeBadges,
  PerspectiveBadge,
  CompanyInfo,
  ReleaseInfo,
  ExpandableText,
  ScreenshotGallery,
} from "@/components/metadata"
import type { Rom, Run } from "@/lib/schemas"
import { NewRunDialog } from "@/components/runs/new-run-dialog"
import { FixMetadataDialog } from "./fix-metadata-dialog"
import { PlayKeybindsDialog } from "./play-keybinds-dialog"

// System display keys → storage keys (matching play-keybinds-dialog.tsx)
const SYSTEM_STORAGE_KEYS: Record<string, string> = {
  nes: "Nes", snes: "Snes", genesis: "Genesis", gba: "Gba",
  gb: "Gb", gbc: "Gb", atari2600: "Atari2600", pce: "PCEngine", tg16: "PCEngine",
}

const DEFAULT_MAPPING: KeyboardMapping = {
  up: "UP", down: "DOWN", left: "LEFT", right: "RIGHT",
  a: "x", b: "z", x: "s", y: "a", l: "q", r: "w",
  start: "RETURN", select: "RSHIFT", c: null, z_btn: null,
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function resolveKeyboardMapping(system: string | undefined, config: any): KeyboardMapping {
  if (!system || !config) return DEFAULT_MAPPING
  const storageKey = SYSTEM_STORAGE_KEYS[system.toLowerCase()] ?? system
  return config.input?.keyboard_mappings?.[storageKey] ?? DEFAULT_MAPPING
}

interface RomDetailSheetProps {
  rom: Rom | undefined
  isLoading: boolean
  isOpen: boolean
  onClose: () => void
  selectedState: string
  onStateChange: (state: string) => void
  onStartRun: () => void
  isStartingRun: boolean
  recentRuns: Run[]
}

export function RomDetailSheet({
  rom,
  isLoading,
  isOpen,
  onClose,
  selectedState,
  onStateChange,
  onStartRun,
  isStartingRun,
  recentRuns,
}: RomDetailSheetProps) {
  const states = rom?.states ?? []

  // Thumbnail URL is now embedded in ROM data
  const thumbnailUrl = rom?.thumbnail_url
  const [imageFailed, setImageFailed] = useState(false)

  // Play keybinds dialog state
  const [showKeybindsDialog, setShowKeybindsDialog] = useState(false)

  // Resolve keyboard mapping for this system
  const { data: appConfig } = useConfig()
  const keyboardMapping = resolveKeyboardMapping(rom?.system, appConfig)

  // Play session
  const { mutate: startPlay, isPending: isStartingPlay, activeSessionId, clearSession } = useStartPlaySession(keyboardMapping)
  const stopPlay = useStopPlaySession()

  // Sync single ROM
  const { mutate: syncRom, isPending: isSyncing } = useSyncRom()

  const handlePlayClick = () => {
    setShowKeybindsDialog(true)
  }

  const handleLaunchGame = () => {
    if (rom) {
      startPlay({ romId: rom.id, state: selectedState || undefined })
    }
  }

  const handleResync = () => {
    if (rom) {
      syncRom({ id: rom.id, force: true })
    }
  }

  const handleStopPlay = () => {
    if (activeSessionId) {
      stopPlay.mutate(activeSessionId)
      clearSession()
    }
  }

  // Display name from ROM (already cleaned by backend)
  const displayName = rom?.display_name || rom?.igdb_name || "Loading..."

  // Check if sync failed
  const syncFailed = rom?.sync_status === "failed"
  const syncPending = rom?.sync_status === "pending"

  return (
    <Sheet open={isOpen} onOpenChange={() => onClose()}>
      <SheetContent className="sm:max-w-2xl w-full flex flex-col p-0 gap-0! overflow-hidden">
        {/* Fixed Header */}
        <SheetHeader className="px-6 py-5 border-b bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/80">
          <div className="flex items-start gap-4">
            {/* Mini Thumbnail */}
            <div className="w-16 h-16 overflow-hidden bg-muted shrink-0">
              {thumbnailUrl && !imageFailed ? (
                <img
                  src={thumbnailUrl}
                  alt={displayName}
                  className="w-full h-full object-contain"
                  onError={() => setImageFailed(true)}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Gamepad2 className="size-8 text-muted-foreground" />
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <SheetTitle className="text-xl truncate">{displayName}</SheetTitle>
              <SheetDescription className="sr-only">
                Game details for {displayName}
              </SheetDescription>
              <div className="flex flex-wrap items-center gap-2 mt-1 text-sm text-muted-foreground">
                {rom && <Badge variant="outline">{rom.system}</Badge>}
                <ReleaseInfo releaseDate={rom?.release_date} variant="compact" />
                <RatingDisplay
                  rating={rom?.rating}
                  ratingCount={rom?.rating_count}
                  variant="compact"
                />
                <CompanyInfo developer={rom?.developer} variant="compact" />
              </div>
            </div>
          </div>
        </SheetHeader>

        {/* Scrollable Content */}
        <ScrollArea className="flex-1">
          <div className="p-6 space-y-6">
            {/* Sync Status Warning */}
            {(syncFailed || syncPending) && (
              <div className={`flex items-center gap-3 p-3 ${syncFailed ? "bg-destructive/10 text-destructive" : "bg-chart-3/10 text-chart-3"}`}>
                <AlertCircle className="size-5 shrink-0" />
                <div className="flex-1 text-sm">
                  {syncFailed ? (
                    <>
                      <p className="font-medium">Metadata sync failed</p>
                      {rom?.sync_error && <p className="text-xs opacity-80">{rom.sync_error}</p>}
                    </>
                  ) : (
                    <p className="font-medium">Metadata pending sync</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleResync}
                    disabled={isSyncing}
                  >
                    <RefreshCw className={`size-4 mr-2 ${isSyncing ? "animate-spin" : ""}`} />
                    {isSyncing ? "Syncing..." : "Retry"}
                  </Button>
                  {syncFailed && rom && (
                    <FixMetadataDialog rom={rom} />
                  )}
                </div>
              </div>
            )}

            {/* Large Cover Image */}
            {thumbnailUrl && !imageFailed && (
              <div className="relative aspect-16/10 bg-muted overflow-hidden shadow-inner">
                <img
                  src={thumbnailUrl}
                  alt={displayName}
                  className="w-full h-full object-contain"
                />
              </div>
            )}

            {/* Game Info Section - uses embedded ROM data */}
            {rom && (
              <div className="space-y-5">
                {/* Genres & Themes */}
                <div className="flex flex-wrap gap-2">
                  <GenreBadges genres={rom.genres} variant="full" />
                  <ThemeBadges themes={rom.themes} variant="full" />
                </div>

                {/* Game Modes & Perspectives */}
                {(rom.game_modes?.length > 0 || rom.player_perspectives?.length > 0) && (
                  <div className="flex flex-wrap gap-2">
                    <GameModeBadges gameModes={rom.game_modes} variant="full" />
                    <PerspectiveBadge perspectives={rom.player_perspectives} variant="full" />
                  </div>
                )}

                {/* Full Rating Display */}
                <RatingDisplay
                  rating={rom.rating}
                  ratingCount={rom.rating_count}
                  variant="full"
                  showCount
                />

                {/* Full Company Info */}
                <CompanyInfo
                  developer={rom.developer}
                  publisher={rom.publisher}
                  variant="full"
                />

                {/* Full Release Info */}
                <ReleaseInfo releaseDate={rom.release_date} variant="full" />

                {/* Summary */}
                {rom.summary && (
                  <ExpandableText
                    text={rom.summary}
                    title="About"
                    maxLines={4}
                  />
                )}

                {/* Storyline (if different from summary) */}
                {rom.storyline && rom.storyline !== rom.summary && (
                  <ExpandableText
                    text={rom.storyline}
                    title="Story"
                    maxLines={6}
                  />
                )}

                {/* Screenshots */}
                <ScreenshotGallery
                  screenshots={rom.screenshot_urls}
                  gameName={rom.display_name}
                  variant="full"
                />

                {/* Manual Correction Option */}
                {rom.sync_status === "synced" && (
                  <div className="pt-2 border-t">
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>Wrong game info?</span>
                      <FixMetadataDialog
                        rom={rom}
                        trigger={
                          <Button variant="ghost" size="sm" className="h-7 text-xs">
                            Fix Metadata
                          </Button>
                        }
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {isLoading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="size-4 border-2 border-muted-foreground/30 border-t-muted-foreground animate-spin" />
                Loading game info...
              </div>
            )}

            <Separator />

            {/* ROM Not Imported Warning */}
            {rom && !rom.has_rom && (
              <div className="flex items-center gap-3 p-3 bg-chart-3/10 text-chart-3">
                <AlertCircle className="size-5 shrink-0" />
                <div className="flex-1 text-sm">
                  <p className="font-medium">ROM file not imported</p>
                  <p className="text-xs opacity-80">
                    This game's ROM file is not available. Import ROMs via Settings to play or train.
                  </p>
                </div>
              </div>
            )}

            {/* Training Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold">Start Training</h4>
                <Link to="/connector-builder" search={{ rom: rom?.id }}>
                  <Button variant="ghost" size="sm" className="h-7 text-xs gap-1">
                    <Wrench className="size-3" />
                    Build Connector
                  </Button>
                </Link>
              </div>

              {/* State Selection */}
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Save State</label>
                {isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading states...</p>
                ) : states.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No save states available.
                    <Link to="/connector-builder" search={{ rom: rom?.id }} className="text-primary hover:underline ml-1">
                      Create a connector
                    </Link>
                    {" "}to enable training.
                  </p>
                ) : (
                  <Select value={selectedState} onValueChange={onStateChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a save state" />
                    </SelectTrigger>
                    <SelectContent>
                      {states.map((state) => (
                        <SelectItem key={state} value={state}>
                          {state}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-3 gap-3">
                {rom && rom.has_rom && !rom.has_connector ? (
                  <Button
                    variant="outline"
                    size="lg"
                    asChild
                  >
                    <Link to="/connector-builder" search={{ rom: rom.id }}>
                      <Wrench className="size-4 mr-2" />
                      Create Connector
                    </Link>
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="lg"
                    disabled={!rom || !rom.has_rom || isStartingPlay}
                    onClick={handlePlayClick}
                    title={rom && !rom.has_rom ? "ROM file not imported" : undefined}
                  >
                    <Gamepad2 className="size-4 mr-2" />
                    {isStartingPlay ? "Launching..." : rom && !rom.has_rom ? "No ROM" : "Play"}
                  </Button>
                )}

                <Button
                  size="lg"
                  disabled={!selectedState || !rom?.has_rom || !rom?.has_connector || isStartingRun}
                  onClick={onStartRun}
                  title={rom && !rom.has_rom ? "ROM file not imported" : rom && !rom.has_connector ? "No connector available" : undefined}
                >
                  <Play className="size-4 mr-2" />
                  {isStartingRun ? "Starting..." : "Train"}
                </Button>

                {rom && (
                  <NewRunDialog
                    initialValues={{ rom: rom.id, state: selectedState || undefined }}
                    trigger={
                      <Button variant="outline" size="lg" disabled={!rom}>
                        <Settings2 className="size-4 mr-2" />
                        Config
                      </Button>
                    }
                  />
                )}
              </div>
            </div>

            {/* Recent Runs */}
            {recentRuns.length > 0 && (
              <>
                <Separator />
                <RecentRunsTable runs={recentRuns} />
              </>
            )}
          </div>
        </ScrollArea>

        {/* Play Keybinds Dialog */}
        {rom && (
          <PlayKeybindsDialog
            open={showKeybindsDialog}
            onOpenChange={setShowKeybindsDialog}
            system={rom.system}
            gameName={rom.display_name || rom.id}
            onLaunch={handleLaunchGame}
            isLaunching={isStartingPlay}
          />
        )}

        {/* Play Frame Viewer Dialog */}
        {activeSessionId && (
          <Dialog
            open
            onOpenChange={(open) => { if (!open) handleStopPlay() }}
          >
            <DialogContent className="sm:max-w-2xl p-4">
              <DialogTitle className="sr-only">
                Playing {rom?.display_name || rom?.id}
              </DialogTitle>
              <PlayFrameViewer
                sessionId={activeSessionId}
                gameName={rom?.display_name || rom?.id || "Game"}
                onStop={handleStopPlay}
                isStopping={stopPlay.isPending}
              />
            </DialogContent>
          </Dialog>
        )}
      </SheetContent>
    </Sheet>
  )
}

function RecentRunsTable({ runs }: { runs: Run[] }) {
  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold">Recent Runs</h4>
      <div className="border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead className="font-medium">State</TableHead>
              <TableHead className="font-medium">Status</TableHead>
              <TableHead className="font-medium">Algorithm</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.id} className="hover:bg-muted/30">
                <TableCell>
                  <Link
                    to="/runs/$runId"
                    params={{ runId: run.id }}
                    className="font-medium hover:underline"
                  >
                    {run.state}
                  </Link>
                </TableCell>
                <TableCell>
                  <StatusBadge status={run.status} />
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {run.algorithm}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
