import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api, type ROM, type Run } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Search, Play, Gamepad2, FolderInput } from "lucide-react"
import { useNavigate, Link } from "@tanstack/react-router"
import { toast } from "sonner"

function StatusBadge({ status }: { status: Run["status"] }) {
  const variants: Record<Run["status"], "default" | "secondary" | "destructive" | "outline"> = {
    running: "default",
    completed: "secondary",
    failed: "destructive",
    stopped: "outline",
    pending: "outline",
  }
  return <Badge variant={variants[status]} className={status === "running" ? "animate-live" : ""}>{status}</Badge>
}

function RomCard({
  rom,
  onSelect,
}: {
  rom: ROM
  onSelect: () => void
}) {
  return (
    <Card
      className="cursor-pointer hover:shadow-lg transition-shadow"
      onClick={onSelect}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base truncate">{rom.name}</CardTitle>
          <Badge variant="outline">{rom.system}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {rom.playable ? "Playable" : "Not configured"}
          </span>
          <Button size="sm" onClick={(e) => { e.stopPropagation(); onSelect() }}>
            <Play className="size-3" />
            Train
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function RomsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")
  const [system, setSystem] = useState<string>("all")
  const [selectedRomId, setSelectedRomId] = useState<string | null>(null)
  const [selectedState, setSelectedState] = useState<string>("")
  const [importPath, setImportPath] = useState("")

  const { data: roms = [], isLoading } = useQuery({
    queryKey: ["roms"],
    queryFn: api.roms.list,
  })

  // Fetch ROM details (including states) when one is selected
  const { data: romDetails, isLoading: isLoadingDetails } = useQuery({
    queryKey: ["rom", selectedRomId],
    queryFn: () => api.roms.get(selectedRomId!),
    enabled: !!selectedRomId,
  })

  // Fetch runs filtered by selected ROM
  const { data: allRuns = [] } = useQuery({
    queryKey: ["runs"],
    queryFn: api.runs.list,
  })

  const romRuns = selectedRomId
    ? allRuns.filter(r => r.rom_id === selectedRomId).slice(0, 5)
    : []

  const importRoms = useMutation({
    mutationFn: api.roms.import,
    onSuccess: (result) => {
      toast.success(`Imported ${result.imported} ROMs`)
      queryClient.invalidateQueries({ queryKey: ["roms"] })
      setImportPath("")
    },
    onError: (error) => {
      toast.error(`Import failed: ${error.message}`)
    },
  })

  const startRun = useMutation({
    mutationFn: (data: { rom_id: string; state: string }) =>
      api.runs.create(data),
    onSuccess: (run) => {
      toast.success("Run started")
      queryClient.invalidateQueries({ queryKey: ["runs"] })
      navigate({ to: "/runs/$runId", params: { runId: run.id } })
    },
    onError: (error) => {
      toast.error(`Failed to start run: ${error.message}`)
    },
  })

  const systems = [...new Set(roms.map((r) => r.system))]

  const filteredRoms = roms.filter((rom) => {
    const matchesSearch = rom.name.toLowerCase().includes(search.toLowerCase())
    const matchesSystem = system === "all" || rom.system === system
    return matchesSearch && matchesSystem
  })

  const handleStartRun = () => {
    if (!selectedRomId || !selectedState) return
    startRun.mutate({ rom_id: selectedRomId, state: selectedState })
  }

  const handleImport = () => {
    if (!importPath.trim()) return
    importRoms.mutate(importPath.trim())
  }

  // Reset state selection when ROM details load
  const states = romDetails?.states ?? []
  if (romDetails && selectedState === "" && states.length > 0) {
    setSelectedState(states[0])
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">ROM Library</h1>
          <p className="text-muted-foreground">Browse and train on your games</p>
        </div>
      </div>

      {/* Import Section */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2">
            <Input
              value={importPath}
              onChange={(e) => setImportPath(e.target.value)}
              placeholder="Path to ROM directory (e.g., /home/user/roms)"
              className="font-mono flex-1"
            />
            <Button onClick={handleImport} disabled={importRoms.isPending || !importPath.trim()}>
              <FolderInput className="size-4" />
              {importRoms.isPending ? "Importing..." : "Import"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="relative flex-1 min-w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            placeholder="Search ROMs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <ToggleGroup
          type="single"
          value={system}
          onValueChange={(v) => v && setSystem(v)}
        >
          <ToggleGroupItem value="all">All</ToggleGroupItem>
          {systems.map((s) => (
            <ToggleGroupItem key={s} value={s}>
              {s}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </div>

      {/* ROM Grid */}
      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">
          Loading ROMs...
        </div>
      ) : filteredRoms.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Gamepad2 className="size-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No ROMs found</p>
          <p className="text-sm">Import ROMs using the path input above</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 stagger-children">
          {filteredRoms.map((rom) => (
            <RomCard
              key={rom.id}
              rom={rom}
              onSelect={() => {
                setSelectedRomId(rom.id)
                setSelectedState("")
              }}
            />
          ))}
        </div>
      )}

      {/* ROM Detail Sheet */}
      <Sheet open={!!selectedRomId} onOpenChange={() => setSelectedRomId(null)}>
        <SheetContent className="sm:max-w-lg">
          {selectedRomId && (
            <>
              <SheetHeader>
                <SheetTitle>{romDetails?.name ?? "Loading..."}</SheetTitle>
                <SheetDescription>
                  {romDetails && <Badge variant="outline">{romDetails.system}</Badge>}
                </SheetDescription>
              </SheetHeader>

              <div className="mt-6 space-y-6">
                {/* State Selection */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Save State</label>
                  {isLoadingDetails ? (
                    <p className="text-sm text-muted-foreground">Loading states...</p>
                  ) : states.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No save states available
                    </p>
                  ) : (
                    <Select
                      value={selectedState}
                      onValueChange={setSelectedState}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select state" />
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

                {/* Start Button */}
                <Button
                  className="w-full"
                  disabled={!selectedState || startRun.isPending}
                  onClick={handleStartRun}
                >
                  <Play className="size-4" />
                  {startRun.isPending ? "Starting..." : "Start Training"}
                </Button>

                {/* Recent Runs for this ROM */}
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Recent Runs</h4>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>State</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Steps</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {romRuns.length === 0 ? (
                        <TableRow>
                          <TableCell
                            colSpan={3}
                            className="text-center text-muted-foreground"
                          >
                            No runs yet
                          </TableCell>
                        </TableRow>
                      ) : (
                        romRuns.map((run) => (
                          <TableRow key={run.id}>
                            <TableCell>
                              <Link
                                to="/runs/$runId"
                                params={{ runId: run.id }}
                                className="hover:underline"
                              >
                                {run.state}
                              </Link>
                            </TableCell>
                            <TableCell>
                              <StatusBadge status={run.status} />
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {run.steps.toLocaleString()}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
