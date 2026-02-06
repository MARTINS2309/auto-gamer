import { useState } from "react"
import { Search, Check, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useSearchIGDB, useResyncRom } from "@/hooks"
import type { Rom, IGDBCandidate } from "@/lib/schemas"

interface FixMetadataDialogProps {
  rom: Rom
  trigger?: React.ReactNode
}

export function FixMetadataDialog({ rom, trigger }: FixMetadataDialogProps) {
  const [open, setOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [activeQuery, setActiveQuery] = useState<string | undefined>(undefined)

  // Search IGDB - only fires when activeQuery is set
  const { data: searchData, isLoading: isSearching } = useSearchIGDB(
    open ? rom.id : null,
    activeQuery
  )

  const resyncRom = useResyncRom()

  const handleSearch = () => {
    setActiveQuery(searchQuery || undefined)
  }

  const handleSelectCandidate = (candidate: IGDBCandidate) => {
    resyncRom.mutate(
      { id: rom.id, data: { igdb_id: candidate.id } },
      {
        onSuccess: () => setOpen(false),
      }
    )
  }

  const candidates = searchData?.candidates ?? []

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            Fix Metadata
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Fix Metadata</DialogTitle>
          <DialogDescription>
            Search IGDB to find the correct game and update metadata for "{rom.display_name}".
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Search Input */}
          <div className="flex gap-2">
            <Input
              placeholder="Search IGDB..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <Button onClick={handleSearch} disabled={isSearching}>
              {isSearching ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Search className="size-4" />
              )}
            </Button>
          </div>

          {/* Results */}
          <ScrollArea className="h-72">
            {isSearching ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="size-6 animate-spin text-muted-foreground" />
              </div>
            ) : candidates.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                {activeQuery !== undefined
                  ? "No results found. Try a different search term."
                  : "Enter a search term to find games on IGDB."}
              </div>
            ) : (
              <div className="space-y-2 pr-4">
                {candidates.map((candidate) => (
                  <CandidateCard
                    key={candidate.id}
                    candidate={candidate}
                    isSelected={rom.igdb_id === candidate.id}
                    onSelect={() => handleSelectCandidate(candidate)}
                    isLoading={resyncRom.isPending}
                  />
                ))}
              </div>
            )}
          </ScrollArea>

          {/* Current Selection */}
          {rom.igdb_id && (
            <div className="text-xs text-muted-foreground border-t pt-3">
              Currently linked to IGDB ID: {rom.igdb_id}
              {rom.igdb_name && ` (${rom.igdb_name})`}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function CandidateCard({
  candidate,
  isSelected,
  onSelect,
  isLoading,
}: {
  candidate: IGDBCandidate
  isSelected: boolean
  onSelect: () => void
  isLoading: boolean
}) {
  return (
    <div
      className={`flex items-center gap-3 p-3 border cursor-pointer transition-colors ${
        isSelected
          ? "border-primary bg-primary/5"
          : "hover:border-primary/50 hover:bg-muted/50"
      }`}
      onClick={onSelect}
    >
      {/* Cover */}
      {candidate.cover_url ? (
        <img
          src={candidate.cover_url}
          alt={candidate.name}
          className="w-12 h-16 object-cover shadow-sm shrink-0"
        />
      ) : (
        <div className="w-12 h-16 bg-muted flex items-center justify-center text-muted-foreground shrink-0">
          ?
        </div>
      )}

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{candidate.name}</p>
        <p className="text-xs text-muted-foreground">
          {candidate.release_date?.split("-")[0] ?? "Unknown year"}
          {candidate.platforms.length > 0 && (
            <span> • {candidate.platforms.slice(0, 2).join(", ")}</span>
          )}
        </p>
        <p className="text-xs text-muted-foreground/70">
          IGDB ID: {candidate.id}
        </p>
      </div>

      {/* Selection indicator */}
      <div className="shrink-0">
        {isLoading ? (
          <Loader2 className="size-5 animate-spin text-primary" />
        ) : isSelected ? (
          <Check className="size-5 text-primary" />
        ) : (
          <div className="size-5 border-2 border-muted-foreground/30" />
        )}
      </div>
    </div>
  )
}
