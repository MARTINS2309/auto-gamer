import { useState, useMemo } from "react"
import { Search } from "lucide-react"
import { Input } from "@/components/ui/input"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Page, PageHeader, PageTitle, PageDescription, PageContent } from "@/components/ui/page"
import { useRoms, useRom, useImportRoms, useRunsByRom, useCreateRun } from "@/hooks"
import { RomGrid, RomImportCard, RomDetailSheet } from "@/components/roms"
import type { Rom } from "@/lib/schemas"

function useRomFilters(roms: Rom[]) {
  const [search, setSearch] = useState("")
  const [system, setSystem] = useState<string>("all")

  const systems = [...new Set(roms.map((r) => r.system))]

  const filteredRoms = roms.filter((rom) => {
    const matchesSearch = rom.name.toLowerCase().includes(search.toLowerCase())
    const matchesSystem = system === "all" || rom.system === system
    return matchesSearch && matchesSystem
  })

  return {
    search,
    setSearch,
    system,
    setSystem,
    systems,
    filteredRoms,
  }
}

export function RomsPage() {
  const { data: roms = [], isLoading } = useRoms()
  const importRoms = useImportRoms()
  const createRun = useCreateRun()

  const [selectedRomId, setSelectedRomId] = useState<string | null>(null)
  const [userSelectedState, setUserSelectedState] = useState<string | null>(null)

  const { data: romDetails, isLoading: isLoadingDetails } = useRom(selectedRomId)
  const recentRuns = useRunsByRom(selectedRomId, 5)

  const filters = useRomFilters(roms)

  // Derive selected state: use user selection, or default to first state
  const selectedState = useMemo(() => {
    if (userSelectedState) return userSelectedState
    return romDetails?.states?.[0] ?? ""
  }, [userSelectedState, romDetails?.states])

  const handleSelectRom = (id: string) => {
    setSelectedRomId(id)
    setUserSelectedState(null) // Reset to auto-select first state
  }

  const handleCloseSheet = () => {
    setSelectedRomId(null)
    setUserSelectedState(null)
  }

  const handleStartRun = () => {
    if (!selectedRomId || !selectedState) return
    createRun.mutate({ rom: selectedRomId, state: selectedState })
  }

  return (
    <Page>
      <PageHeader>
        <PageTitle>ROM Library</PageTitle>
        <PageDescription>Browse and train on your games</PageDescription>
      </PageHeader>

      <PageContent className="space-y-6">
        {/* Import Section */}
        <RomImportCard
          onImport={importRoms.mutate}
          isPending={importRoms.isPending}
        />

        {/* Filters */}
        <div className="flex items-center gap-4 flex-wrap">
          <div className="relative flex-1 min-w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Search ROMs..."
              value={filters.search}
              onChange={(e) => filters.setSearch(e.target.value)}
              className="pl-9"
            />
          </div>

          <ToggleGroup
            type="single"
            value={filters.system}
            onValueChange={(v) => v && filters.setSystem(v)}
          >
            <ToggleGroupItem value="all">All</ToggleGroupItem>
            {filters.systems.map((s) => (
              <ToggleGroupItem key={s} value={s}>
                {s}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>

        {/* ROM Grid */}
        <RomGrid
          roms={filters.filteredRoms}
          isLoading={isLoading}
          onSelectRom={handleSelectRom}
        />

        {/* ROM Detail Sheet */}
        <RomDetailSheet
          rom={romDetails}
          isLoading={isLoadingDetails}
          isOpen={!!selectedRomId}
          onClose={handleCloseSheet}
          selectedState={selectedState}
          onStateChange={setUserSelectedState}
          onStartRun={handleStartRun}
          isStartingRun={createRun.isPending}
          recentRuns={recentRuns}
        />
      </PageContent>
    </Page>
  )
}
