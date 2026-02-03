import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Play, Settings2, Gamepad2 } from "lucide-react"
import { Link } from "@tanstack/react-router"
import { StatusBadge } from "@/components/shared"
import { useThumbnail, useGameMetadata, useStartPlaySession } from "@/hooks"
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
  // Use rom.id as correlation key (matches batch fetch)
  const { data: metadata, isLoading: metadataLoading } = useGameMetadata(
    rom?.system ?? null,
    rom?.id ?? null
  )
  const { url: thumbnailUrl } = useThumbnail(rom?.id ?? "", rom?.system ?? "", "boxart")

  // Play session
  const { mutate: startPlay, isPending: isStartingPlay } = useStartPlaySession()

  const handlePlayGame = () => {
    if (rom) {
      startPlay({ romId: rom.id, state: selectedState || undefined })
    }
  }

  // Show proper game name from metadata, fallback to ROM id
  const displayName = metadata?.name || rom?.name || "Loading..."

  return (
    <Sheet open={isOpen} onOpenChange={() => onClose()}>
      <SheetContent className="sm:max-w-2xl w-full flex flex-col p-0 gap-0! overflow-hidden">
        {/* Fixed Header */}
        <SheetHeader className="px-6 py-5 border-b bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/80">
          <div className="flex items-start gap-4">
            {/* Mini Thumbnail */}
            <div className="w-16 h-16 rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-800 shrink-0">
              {thumbnailUrl ? (
                <img
                  src={thumbnailUrl}
                  alt={displayName}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Gamepad2 className="size-8 text-slate-400" />
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
                <ReleaseInfo releaseDate={metadata?.release_date} variant="compact" />
                <RatingDisplay
                  rating={metadata?.rating}
                  ratingCount={metadata?.rating_count}
                  variant="compact"
                />
                <CompanyInfo developer={metadata?.developer} variant="compact" />
              </div>
            </div>
          </div>
        </SheetHeader>

        {/* Scrollable Content */}
        <ScrollArea className="flex-1">
          <div className="p-6 space-y-6">
            {/* Large Cover Image */}
            {thumbnailUrl && (
              <div className="relative aspect-16/10 bg-linear-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-900 rounded-xl overflow-hidden shadow-inner">
                <img
                  src={thumbnailUrl}
                  alt={displayName}
                  className="w-full h-full object-contain"
                />
              </div>
            )}

            {/* Game Info Section */}
            {metadata && (
              <div className="space-y-5">
                {/* Genres & Themes */}
                <div className="flex flex-wrap gap-2">
                  <GenreBadges genres={metadata.genres} variant="full" />
                  <ThemeBadges themes={metadata.themes} variant="full" />
                </div>

                {/* Game Modes & Perspectives */}
                {(metadata.game_modes?.length > 0 || metadata.player_perspectives?.length > 0) && (
                  <div className="flex flex-wrap gap-2">
                    <GameModeBadges gameModes={metadata.game_modes} variant="full" />
                    <PerspectiveBadge perspectives={metadata.player_perspectives} variant="full" />
                  </div>
                )}

                {/* Full Rating Display */}
                <RatingDisplay
                  rating={metadata.rating}
                  ratingCount={metadata.rating_count}
                  variant="full"
                  showCount
                />

                {/* Full Company Info */}
                <CompanyInfo
                  developer={metadata.developer}
                  publisher={metadata.publisher}
                  variant="full"
                />

                {/* Full Release Info */}
                <ReleaseInfo releaseDate={metadata.release_date} variant="full" />

                {/* Summary */}
                {metadata.summary && (
                  <ExpandableText
                    text={metadata.summary}
                    title="About"
                    maxLines={4}
                  />
                )}

                {/* Storyline (if different from summary) */}
                {metadata.storyline && metadata.storyline !== metadata.summary && (
                  <ExpandableText
                    text={metadata.storyline}
                    title="Story"
                    maxLines={6}
                  />
                )}

                {/* Screenshots */}
                <ScreenshotGallery
                  screenshots={metadata.screenshot_urls}
                  gameName={metadata.name}
                  variant="full"
                />
              </div>
            )}

            {metadataLoading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="size-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
                Loading game info...
              </div>
            )}

            <Separator />

            {/* Training Section */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold">Start Training</h4>

              {/* State Selection */}
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Save State</label>
                {isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading states...</p>
                ) : states.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No save states available</p>
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
                <Button
                  variant="outline"
                  size="lg"
                  disabled={!rom || isStartingPlay}
                  onClick={handlePlayGame}
                >
                  <Gamepad2 className="size-4 mr-2" />
                  {isStartingPlay ? "Launching..." : "Play"}
                </Button>

                <Button
                  size="lg"
                  disabled={!selectedState || isStartingRun}
                  onClick={onStartRun}
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
      </SheetContent>
    </Sheet>
  )
}

function RecentRunsTable({ runs }: { runs: Run[] }) {
  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold">Recent Runs</h4>
      <div className="rounded-lg border overflow-hidden">
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
