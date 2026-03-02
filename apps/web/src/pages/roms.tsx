import { useState, useMemo } from "react"
import { Search, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Page,
  PageHeader,
  PageHeaderNav,
  PageHeaderItem,
  PageTitle,
  PageContent,
} from "@/components/ui/page"
import { Badge } from "@/components/ui/badge"
import { ButtonGroup, ButtonGroupSeparator } from "@/components/ui/button-group"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { useRoms, useRom, useRunsByRom } from "@/hooks"
import { RomGrid, RomDetailSheet } from "@/components/roms"
import { NewRunDialog } from "@/components/runs/new-run-dialog"
import type { RomListItem } from "@/lib/schemas"

function useRomFilters(roms: RomListItem[]) {
  const [search, setSearch] = useState("")
  const [system, setSystem] = useState<string>("all")
  const [genre, setGenre] = useState<string>("all")
  const [developer, setDeveloper] = useState<string>("all")
  const [minRating, setMinRating] = useState<string>("all")
  const [statusFilter, setStatusFilter] = useState<string>("all")

  const systems = useMemo(() =>
    [...new Set(roms.map((r) => r.system))].sort(),
    [roms]
  )

  const genres = useMemo(() => {
    const allGenres = roms.flatMap((r) => r.genres ?? [])
    return [...new Set(allGenres)].sort()
  }, [roms])

  const developers = useMemo(() => {
    const allDevs = roms.map((r) => r.developer).filter(Boolean) as string[]
    return [...new Set(allDevs)].sort()
  }, [roms])

  const filteredRoms = useMemo(() => {
    return roms.filter((rom) => {
      const matchesSearch = rom.display_name.toLowerCase().includes(search.toLowerCase())
      const matchesSystem = system === "all" || rom.system === system
      const matchesGenre = genre === "all" || (rom.genres ?? []).includes(genre)
      const matchesDeveloper = developer === "all" || rom.developer === developer
      const matchesRating = minRating === "all" || (rom.rating ?? 0) >= parseInt(minRating)
      const matchesStatus = statusFilter === "all" || rom.status === statusFilter
      return matchesSearch && matchesSystem && matchesGenre && matchesDeveloper && matchesRating && matchesStatus
    })
  }, [roms, search, system, genre, developer, minRating, statusFilter])

  const activeFilterCount = [system, genre, developer, minRating, statusFilter].filter(v => v !== "all").length

  const clearFilters = () => {
    setSystem("all")
    setGenre("all")
    setDeveloper("all")
    setMinRating("all")
    setStatusFilter("all")
    setSearch("")
  }

  return {
    search,
    setSearch,
    system,
    setSystem,
    genre,
    setGenre,
    developer,
    setDeveloper,
    minRating,
    setMinRating,
    statusFilter,
    setStatusFilter,
    systems,
    genres,
    developers,
    filteredRoms,
    activeFilterCount,
    clearFilters,
  }
}

export function RomsPage() {
  const [showConnectors, setShowConnectors] = useState(false)
  const { data: roms = [], isLoading } = useRoms(showConnectors)

  const [selectedRomId, setSelectedRomId] = useState<string | null>(null)
  const [userSelectedState, setUserSelectedState] = useState<string | null>(null)
  const [newRunOpen, setNewRunOpen] = useState(false)

  const { data: romDetails, isLoading: isLoadingDetails } = useRom(selectedRomId)
  const recentRuns = useRunsByRom(selectedRomId, 5)

  const filters = useRomFilters(roms)

  const selectedState = useMemo(() => {
    if (userSelectedState) return userSelectedState
    return romDetails?.states?.[0] ?? ""
  }, [userSelectedState, romDetails?.states])

  const handleSelectRom = (id: string) => {
    setSelectedRomId(id)
    setUserSelectedState(null)
  }

  const handleCloseSheet = () => {
    setSelectedRomId(null)
    setUserSelectedState(null)
  }

  const handleStartRun = () => {
    if (!selectedRomId || !selectedState) return
    setNewRunOpen(true)
  }

  return (
    <Page>
      <PageHeader hideOnScroll={false}>
        <PageHeaderNav>
          <PageHeaderItem>
            <PageTitle>ROM Library</PageTitle>
          </PageHeaderItem>

          <PageHeaderItem>
            <ButtonGroup>
              <ButtonGroup className="flex-1 min-w-64">
                <InputGroup>
                  <InputGroupAddon>
                    <Search />
                  </InputGroupAddon>
                  <InputGroupInput
                    placeholder="Search ROMs..."
                    value={filters.search}
                    onChange={(e) => filters.setSearch(e.target.value)}
                  />
                </InputGroup>
              </ButtonGroup>

              <ButtonGroupSeparator />

              <ButtonGroup>
                <Select value={filters.system} onValueChange={filters.setSystem}>
                  <SelectTrigger className="w-36">
                    <SelectValue placeholder="Platform" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Platforms</SelectItem>
                    {filters.systems.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </ButtonGroup>

              <ButtonGroup>
                <Select value={filters.genre} onValueChange={filters.setGenre}>
                  <SelectTrigger className="w-36">
                    <SelectValue placeholder="Genre" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Genres</SelectItem>
                    {filters.genres.map((g) => (
                      <SelectItem key={g} value={g}>{g}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </ButtonGroup>

              <ButtonGroup>
                <Select value={filters.developer} onValueChange={filters.setDeveloper}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Developer" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Developers</SelectItem>
                    {filters.developers.map((d) => (
                      <SelectItem key={d} value={d}>{d}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </ButtonGroup>

              <ButtonGroup>
                <Select value={filters.minRating} onValueChange={filters.setMinRating}>
                  <SelectTrigger className="w-28">
                    <SelectValue placeholder="Rating" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Ratings</SelectItem>
                    <SelectItem value="80">80+</SelectItem>
                    <SelectItem value="70">70+</SelectItem>
                    <SelectItem value="60">60+</SelectItem>
                    <SelectItem value="50">50+</SelectItem>
                  </SelectContent>
                </Select>
              </ButtonGroup>

              <ButtonGroup>
                <Select value={filters.statusFilter} onValueChange={filters.setStatusFilter}>
                  <SelectTrigger className="w-36">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Games</SelectItem>
                    <SelectItem value="trainable">Ready to Train</SelectItem>
                    <SelectItem value="playable">Playable Only</SelectItem>
                    <SelectItem value="connector_only">Need ROM</SelectItem>
                  </SelectContent>
                </Select>
              </ButtonGroup>

              {filters.activeFilterCount > 0 && (
                <ButtonGroup>
                  <Button
                    variant="ghost"
                    onClick={filters.clearFilters}
                    className="text-muted-foreground"
                  >
                    <X className="size-4 mr-1" />
                    Clear ({filters.activeFilterCount})
                  </Button>
                </ButtonGroup>
              )}
            </ButtonGroup>
          </PageHeaderItem>

          <PageHeaderItem className="ml-auto flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Switch
                id="show-connectors"
                checked={showConnectors}
                onCheckedChange={setShowConnectors}
              />
              <Label htmlFor="show-connectors" className="text-sm text-muted-foreground cursor-pointer">
                Show Connectors
              </Label>
            </div>
            <Badge variant="secondary" className="text-xs">
              {filters.filteredRoms.length} of {roms.length}
            </Badge>
          </PageHeaderItem>
        </PageHeaderNav>
      </PageHeader>

      <PageContent>
        <RomGrid
          roms={filters.filteredRoms}
          isLoading={isLoading}
          onSelectRom={handleSelectRom}
          totalCount={roms.length}
          onClearFilters={filters.clearFilters}
        />

        <RomDetailSheet
          rom={romDetails}
          isLoading={isLoadingDetails}
          isOpen={!!selectedRomId}
          onClose={handleCloseSheet}
          selectedState={selectedState}
          onStateChange={setUserSelectedState}
          onStartRun={handleStartRun}
          isStartingRun={false}
          recentRuns={recentRuns}
        />

        <NewRunDialog
          open={newRunOpen}
          onOpenChange={setNewRunOpen}
          initialValues={selectedRomId && selectedState ? { rom: selectedRomId, state: selectedState } : undefined}
        />
      </PageContent>
    </Page>
  )
}
