import { useEffect, useState } from "react"
import { Link, useSearch } from "@tanstack/react-router"
import {
  Page,
  PageHeader,
  PageHeaderNav,
  PageHeaderItem,
  PageContent,
} from "@/components/ui/page"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {
  Play,
  Search,
  Plus,
  Trash2,
  Save,
  FileCode,
  Gamepad2,
  MemoryStick,
  Target,
  Flag,
  Download,
  Eye,
  Pause,
  SkipForward,
  X,
  ChevronRight,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useConnectorBuilder } from "@/hooks"

export default function ConnectorBuilderPage() {
  const { rom: romIdParam } = useSearch({ from: "/connector-builder" })

  const {
    session,
    isStarting,
    startError,
    screenImage,
    frameCount,
    searches,
    watchValues,
    watches,
    savedStates,
    isPlaying,
    startSession,
    closeSession,
    stepFrames,
    startPlaying,
    stopPlaying,
    refreshScreen,
    searchMemory,
    deltaSearch,
    removeSearch,
    addWatch,
    removeWatch,
    refreshWatches,
    addReward,
    addDoneCondition,
    saveState,
    loadState,
    refreshStates,
    exportConnector,
  } = useConnectorBuilder()

  const [step, setStep] = useState<1 | 2 | 3 | 4>(1)

  // Search form state
  const [searchName, setSearchName] = useState("search1")
  const [searchValue, setSearchValue] = useState("")
  const [searchType, setSearchType] = useState<"exact" | "equal" | "greater-than" | "less-than" | "not-equal">("exact")
  const [activeSearchName, setActiveSearchName] = useState<string | null>(null)
  const [searchHistory, setSearchHistory] = useState<Record<string, Array<{ op: string; value: number; count: number }>>>({})

  // Watch form state
  const [newWatchName, setNewWatchName] = useState("")
  const [newWatchAddress, setNewWatchAddress] = useState("")
  const [newWatchType, setNewWatchType] = useState("|u1")

  // Reward form state
  const [rewardVariable, setRewardVariable] = useState("")
  const [rewardOperation, setRewardOperation] = useState("delta")
  const [rewardMultiplier, setRewardMultiplier] = useState("1.0")

  // Done condition form state
  const [doneVariable, setDoneVariable] = useState("")
  const [doneOperation, setDoneOperation] = useState("equal")
  const [doneReference, setDoneReference] = useState("0")

  // State save form
  const [stateName, setStateName] = useState("")

  // Auto-start if rom param provided (once per rom param)
  useEffect(() => {
    if (romIdParam && !session && !isStarting && !startError) {
      startSession(romIdParam)
    }
  }, [romIdParam, session, isStarting, startError, startSession])

  // Refresh watches periodically when session active
  useEffect(() => {
    if (!session || Object.keys(watches).length === 0) return
    const interval = setInterval(refreshWatches, 1000)
    return () => clearInterval(interval)
  }, [session, watches, refreshWatches])

  // Refresh states on step change
  useEffect(() => {
    if (session && step === 4) {
      refreshStates()
    }
  }, [session, step, refreshStates])

  const handleSearch = async () => {
    if (!searchValue) return
    const val = parseInt(searchValue, 10)
    if (isNaN(val)) return

    let result
    if (searchType === "exact") {
      // Reset history for fresh exact search on existing name
      if (searches[searchName]) {
        setSearchHistory(prev => ({ ...prev, [searchName]: [] }))
      }
      result = await searchMemory(searchName, val)
    } else {
      result = await deltaSearch(searchName, searchType, val)
    }

    if (result) {
      // Track history
      setSearchHistory(prev => ({
        ...prev,
        [searchName]: [
          ...(prev[searchName] ?? []),
          { op: searchType, value: val, count: result.num_results },
        ],
      }))
      // Auto-select this search
      setActiveSearchName(searchName)
      // Clear value and switch to delta mode for refinement
      setSearchValue("")
      if (searchType === "exact") {
        setSearchType("not-equal")
      }
    }
  }

  const handleRemoveSearch = async (name: string) => {
    await removeSearch(name)
    if (activeSearchName === name) setActiveSearchName(null)
    setSearchHistory(prev => {
      const next = { ...prev }
      delete next[name]
      return next
    })
  }

  const handleQuickWatch = async (address: number, type: string, name: string) => {
    await addWatch(name, address, type)
  }

  const handleNewSearch = () => {
    const nextNum = Object.keys(searches).length + 1
    setActiveSearchName(null)
    setSearchName(`search${nextNum}`)
    setSearchValue("")
    setSearchType("exact")
  }

  const handleAddWatch = async () => {
    if (!newWatchName || !newWatchAddress) return
    const addr = parseInt(newWatchAddress, 16) || parseInt(newWatchAddress, 10)
    if (isNaN(addr)) return
    await addWatch(newWatchName, addr, newWatchType)
    setNewWatchName("")
    setNewWatchAddress("")
  }

  const handleAddReward = async () => {
    if (!rewardVariable) return
    await addReward(rewardVariable, rewardOperation, 0, parseFloat(rewardMultiplier) || 1.0)
    setRewardVariable("")
    setRewardMultiplier("1.0")
  }

  const handleAddDone = async () => {
    if (!doneVariable) return
    await addDoneCondition(doneVariable, doneOperation, parseFloat(doneReference) || 0)
    setDoneVariable("")
    setDoneReference("0")
  }

  const handleSaveState = async () => {
    if (!stateName) return
    await saveState(stateName)
    setStateName("")
  }

  const handleExport = async () => {
    const result = await exportConnector()
    if (result) {
      // Success — could navigate to ROM detail
    }
  }

  // --- Helpers & derived values ---

  const activeSearch = activeSearchName ? searches[activeSearchName] : null

  function formatCount(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
    return n.toString()
  }

  function formatOp(op: string): string {
    switch (op) {
      case "exact": return "="
      case "greater-than": return "↑"
      case "less-than": return "↓"
      case "equal": return "=="
      case "not-equal": return "≠"
      default: return op
    }
  }

  function getSearchStatus(count: number) {
    if (count === 0) return "empty" as const
    if (count === 1) return "found" as const
    if (count <= 100) return "close" as const
    if (count <= 10000) return "narrowing" as const
    return "broad" as const
  }

  const statusBadgeClasses: Record<ReturnType<typeof getSearchStatus>, string> = {
    broad: "bg-muted text-muted-foreground",
    narrowing: "bg-secondary text-secondary-foreground",
    close: "bg-accent text-accent-foreground",
    found: "bg-primary text-primary-foreground",
    empty: "bg-destructive/15 text-destructive",
  }

  // Not started yet — show start prompt
  if (!session) {
    return (
      <Page>
        <PageHeader>
          <PageHeaderNav>
            <PageHeaderItem>
              <Breadcrumb>
                <BreadcrumbList>
                  <BreadcrumbItem>
                    <BreadcrumbLink asChild>
                      <Link to="/roms">ROMs</Link>
                    </BreadcrumbLink>
                  </BreadcrumbItem>
                  <BreadcrumbSeparator />
                  <BreadcrumbItem>
                    <BreadcrumbPage>Connector Builder</BreadcrumbPage>
                  </BreadcrumbItem>
                </BreadcrumbList>
              </Breadcrumb>
            </PageHeaderItem>
          </PageHeaderNav>
        </PageHeader>
        <PageContent>
          <div className="max-w-md mx-auto mt-20 text-center space-y-4">
            <Gamepad2 className="size-12 mx-auto text-muted-foreground" />
            <h2 className="text-xl font-bold">Connector Builder</h2>
            <p className="text-muted-foreground">
              {isStarting
                ? "Starting builder session..."
                : startError
                  ? `Failed to start: ${startError}`
                  : romIdParam
                    ? "Initializing..."
                    : "Select a ROM from the library to start building a connector."}
            </p>
            {startError && romIdParam && (
              <Button onClick={() => startSession(romIdParam)}>Retry</Button>
            )}
            <Link to="/roms">
              <Button variant="outline">Browse ROMs</Button>
            </Link>
          </div>
        </PageContent>
      </Page>
    )
  }

  return (
    <Page>
      <PageHeader>
        <PageHeaderNav>
          <PageHeaderItem>
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbLink asChild>
                    <Link to="/roms">ROMs</Link>
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbPage>Connector Builder</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </PageHeaderItem>
        </PageHeaderNav>
      </PageHeader>

      <PageContent>
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Connector Builder</h1>
              <p className="text-muted-foreground">
                Create a training connector for <span className="font-medium">{session.rom_name}</span>
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">{session.system}</Badge>
              <Badge variant="secondary">{session.game_name}</Badge>
              <Button variant="ghost" size="sm" onClick={closeSession}>
                <X className="size-4" />
              </Button>
            </div>
          </div>

          {/* Progress Steps */}
          <div className="flex items-center gap-2">
            {[
              { n: 1, label: "Setup ROM" },
              { n: 2, label: "Find Memory" },
              { n: 3, label: "Define Rewards" },
              { n: 4, label: "Save States" },
            ].map(({ n, label }) => (
              <button
                key={n}
                onClick={() => setStep(n as 1 | 2 | 3 | 4)}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors ${
                  step === n
                    ? "bg-primary text-primary-foreground"
                    : step > n
                    ? "bg-primary/20 text-primary"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                <span className="w-5 h-5 flex items-center justify-center text-xs border">
                  {n}
                </span>
                {label}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-6">
            {/* Main Content */}
            <div className="col-span-2 space-y-6">
              {step === 1 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileCode className="size-5" />
                      ROM Setup
                    </CardTitle>
                    <CardDescription>
                      ROM loaded and environment initialized. You can proceed to memory search.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Game Name</Label>
                        <Input value={session.game_name} readOnly className="font-mono" />
                      </div>
                      <div className="space-y-2">
                        <Label>System</Label>
                        <Input value={session.system} readOnly className="font-mono" />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Available Buttons</Label>
                      <div className="flex flex-wrap gap-1">
                        {session.buttons.filter((btn): btn is string => btn !== null).map(btn => (
                          <Badge key={btn} variant="outline" className="text-xs">{btn}</Badge>
                        ))}
                      </div>
                    </div>

                    <Separator />

                    {/* Emulator controls */}
                    <div className="flex items-center gap-2 p-3 bg-muted">
                      <Button
                        variant={isPlaying ? "destructive" : "default"}
                        size="sm"
                        onClick={isPlaying ? stopPlaying : startPlaying}
                      >
                        {isPlaying ? (
                          <><Pause className="size-4 mr-2" />Pause</>
                        ) : (
                          <><Play className="size-4 mr-2" />Play</>
                        )}
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => stepFrames(60)}>
                        <SkipForward className="size-4 mr-2" />
                        +60 frames
                      </Button>
                      <div className="flex-1" />
                      <span className="text-sm text-muted-foreground">
                        Frame: {frameCount.toLocaleString()}
                      </span>
                    </div>

                    <div className="text-sm text-muted-foreground space-y-1">
                      <p>Press <strong>Play</strong> to run the emulator, then use your keyboard to control the game:</p>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs">
                        <span>Arrows: D-Pad</span>
                        <span>X: A</span>
                        <span>Z: B</span>
                        <span>Enter: START</span>
                        <span>Shift: SELECT</span>
                        {session.buttons.some(b => b === "X") && <span>S: X</span>}
                        {session.buttons.some(b => b === "Y") && <span>A: Y</span>}
                        {session.buttons.some(b => b === "L") && <span>Q: L</span>}
                        {session.buttons.some(b => b === "R") && <span>W: R</span>}
                        {session.buttons.some(b => b === "C") && <span>D: C</span>}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {step === 2 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <MemoryStick className="size-5" />
                      Memory Search
                    </CardTitle>
                    <CardDescription>
                      Find memory addresses for game values (score, lives, health, position)
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Game Controls */}
                    <div className="flex items-center gap-2 p-3 bg-muted">
                      <Button
                        variant={isPlaying ? "destructive" : "default"}
                        size="sm"
                        onClick={isPlaying ? stopPlaying : startPlaying}
                      >
                        {isPlaying ? (
                          <><Pause className="size-4 mr-2" />Pause</>
                        ) : (
                          <><Play className="size-4 mr-2" />Play</>
                        )}
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => stepFrames(60)}>
                        <SkipForward className="size-4 mr-2" />
                        +60 frames
                      </Button>
                      <div className="flex-1" />
                      <span className="text-sm text-muted-foreground">
                        Frame: {frameCount.toLocaleString()}
                      </span>
                    </div>

                    {/* Search Form */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-medium">
                          {activeSearchName && searches[activeSearchName]
                            ? `Refine "${activeSearchName}"`
                            : "New Search"}
                        </h4>
                        {activeSearchName && (
                          <Button variant="ghost" size="sm" onClick={handleNewSearch}>
                            <Plus className="size-3 mr-1" />
                            New Search
                          </Button>
                        )}
                      </div>
                      <div className="grid grid-cols-5 gap-2">
                        <Input
                          placeholder="Search name"
                          value={searchName}
                          onChange={(e) => setSearchName(e.target.value)}
                          disabled={!!activeSearchName}
                        />
                        <Input
                          type="number"
                          placeholder="Value..."
                          value={searchValue}
                          onChange={(e) => setSearchValue(e.target.value)}
                        />
                        <Select value={searchType} onValueChange={(v) => setSearchType(v as typeof searchType)}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="exact">Exact Value</SelectItem>
                            <SelectItem value="greater-than">Increased</SelectItem>
                            <SelectItem value="less-than">Decreased</SelectItem>
                            <SelectItem value="equal">Unchanged</SelectItem>
                            <SelectItem value="not-equal">Changed</SelectItem>
                          </SelectContent>
                        </Select>
                        <Button onClick={handleSearch} className="col-span-2">
                          <Search className="size-4 mr-2" />
                          {activeSearchName ? "Refine" : "Search"}
                        </Button>
                      </div>
                      {Object.keys(searches).length === 0 && (
                        <p className="text-xs text-muted-foreground">
                          Search for a known value (e.g. score = 0), play until it changes, then refine with Increased/Decreased.
                        </p>
                      )}
                    </div>

                    {/* Active Searches List */}
                    {Object.keys(searches).length > 0 && (
                      <>
                        <Separator />
                        <div className="space-y-1">
                          <h4 className="text-sm font-medium mb-2">Searches</h4>
                          {Object.entries(searches).map(([name, result]) => {
                            const status = getSearchStatus(result.num_results)
                            const isActive = activeSearchName === name
                            const history = searchHistory[name] ?? []
                            return (
                              <button
                                key={name}
                                onClick={() => {
                                  setActiveSearchName(name)
                                  setSearchName(name)
                                  if (searchType === "exact") setSearchType("not-equal")
                                }}
                                className={cn(
                                  "w-full flex items-center gap-3 p-2 text-sm text-left transition-colors",
                                  isActive
                                    ? "bg-muted border-l-2 border-primary"
                                    : "hover:bg-muted/50"
                                )}
                              >
                                <span className="font-medium min-w-[60px]">{name}</span>
                                {/* History trail */}
                                <span className="flex items-center gap-1 text-xs text-muted-foreground flex-1 overflow-hidden">
                                  {history.map((h, i) => (
                                    <span key={i} className="flex items-center gap-1 shrink-0">
                                      {i > 0 && <ChevronRight className="size-3" />}
                                      <span>{formatOp(h.op)}{h.op === "exact" ? h.value : ""}</span>
                                      <span className="font-mono">{formatCount(h.count)}</span>
                                    </span>
                                  ))}
                                </span>
                                {/* Status badge */}
                                <span className={cn(
                                  "px-2 py-0.5 text-xs font-medium shrink-0",
                                  statusBadgeClasses[status]
                                )}>
                                  {status === "found" ? "Found!" : formatCount(result.num_results)}
                                </span>
                                <Button
                                  variant="ghost"
                                  size="icon-xs"
                                  onClick={(e) => { e.stopPropagation(); handleRemoveSearch(name) }}
                                >
                                  <X className="size-3" />
                                </Button>
                              </button>
                            )
                          })}
                        </div>
                      </>
                    )}

                    {/* Results Panel for Active Search */}
                    {activeSearch && (
                      <>
                        <Separator />
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-medium">
                              Results for &ldquo;{activeSearchName}&rdquo;
                            </h4>
                            <span className="text-sm text-muted-foreground">
                              {activeSearch.num_results.toLocaleString()} match{activeSearch.num_results !== 1 ? "es" : ""}
                            </span>
                          </div>

                          {/* Unique result — found! */}
                          {activeSearch.unique && (
                            <div className="border-2 border-primary/50 bg-primary/5 p-4 flex items-center justify-between">
                              <div>
                                <p className="text-sm font-medium text-primary mb-1">
                                  Address Found
                                </p>
                                <p className="text-2xl font-mono font-bold">
                                  0x{activeSearch.unique.address.toString(16).toUpperCase()}
                                </p>
                                <Badge variant="outline" className="mt-1">{activeSearch.unique.type}</Badge>
                              </div>
                              <Button
                                onClick={() => handleQuickWatch(
                                  activeSearch.unique!.address,
                                  activeSearch.unique!.type,
                                  activeSearchName!
                                )}
                                disabled={!!watches[activeSearchName!]}
                              >
                                <Eye className="size-4 mr-2" />
                                {watches[activeSearchName!] ? "Watching" : "Add Watch"}
                              </Button>
                            </div>
                          )}

                          {/* Viewable results (2-100) */}
                          {!activeSearch.unique && activeSearch.results.length > 0 && (
                            <ScrollArea className="h-56 border">
                              <table className="w-full text-sm">
                                <thead className="bg-muted sticky top-0">
                                  <tr>
                                    <th className="text-left p-2">Address</th>
                                    <th className="text-left p-2">Types</th>
                                    <th className="p-2"></th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {activeSearch.results.map((r) => (
                                    <tr key={r.address} className="border-t hover:bg-muted/50">
                                      <td className="p-2 font-mono text-xs">
                                        0x{r.address.toString(16).toUpperCase()}
                                      </td>
                                      <td className="p-2">
                                        <div className="flex gap-1 flex-wrap">
                                          {r.types.map((t) => (
                                            <Badge key={t} variant="outline" className="text-xs">{t}</Badge>
                                          ))}
                                        </div>
                                      </td>
                                      <td className="p-2 text-right">
                                        <Button
                                          variant="outline"
                                          size="sm"
                                          onClick={() => handleQuickWatch(r.address, r.types[0], `${activeSearchName}_${r.address.toString(16)}`)}
                                        >
                                          <Plus className="size-3 mr-1" />
                                          Watch
                                        </Button>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </ScrollArea>
                          )}

                          {/* Too many results */}
                          {!activeSearch.unique && activeSearch.results.length === 0 && activeSearch.num_results > 0 && (
                            <div className="p-4 border text-center text-sm text-muted-foreground">
                              <p className="font-medium">{activeSearch.num_results.toLocaleString()} matches</p>
                              <p className="mt-1">
                                Play the game to change the value, then refine with Increased / Decreased / Changed.
                              </p>
                            </div>
                          )}

                          {/* No results */}
                          {activeSearch.num_results === 0 && (
                            <div className="p-4 border border-destructive/30 text-center text-sm text-destructive">
                              No matches found. Try a different value or start a new search.
                            </div>
                          )}
                        </div>
                      </>
                    )}

                    <Separator />

                    {/* Watches */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-medium">Memory Watches</h4>
                      </div>

                      {/* Add watch form */}
                      <div className="grid grid-cols-5 gap-2 mb-3">
                        <Input
                          placeholder="Name"
                          value={newWatchName}
                          onChange={(e) => setNewWatchName(e.target.value)}
                        />
                        <Input
                          placeholder="0x1234"
                          value={newWatchAddress}
                          onChange={(e) => setNewWatchAddress(e.target.value)}
                          className="font-mono"
                        />
                        <Select value={newWatchType} onValueChange={setNewWatchType}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="|u1">u8</SelectItem>
                            <SelectItem value="<u2">u16</SelectItem>
                            <SelectItem value="<u4">u32</SelectItem>
                            <SelectItem value="|i1">i8</SelectItem>
                            <SelectItem value="<i2">i16</SelectItem>
                            <SelectItem value="<i4">i32</SelectItem>
                          </SelectContent>
                        </Select>
                        <Button onClick={handleAddWatch} className="col-span-2">
                          <Plus className="size-4 mr-2" />
                          Add Watch
                        </Button>
                      </div>

                      {Object.keys(watches).length > 0 ? (
                        <ScrollArea className="h-48 border">
                          <table className="w-full text-sm">
                            <thead className="bg-muted sticky top-0">
                              <tr>
                                <th className="text-left p-2">Name</th>
                                <th className="text-left p-2">Address</th>
                                <th className="text-left p-2">Type</th>
                                <th className="text-right p-2">Value</th>
                                <th className="p-2"></th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(watches).map(([name, w]) => (
                                <tr key={name} className="border-t hover:bg-muted/50">
                                  <td className="p-2 font-medium">{name}</td>
                                  <td className="p-2 font-mono text-xs">0x{w.address.toString(16).toUpperCase()}</td>
                                  <td className="p-2">
                                    <Badge variant="outline" className="text-xs">{w.type}</Badge>
                                  </td>
                                  <td className="p-2 text-right font-mono">
                                    {watchValues[name] ?? "—"}
                                  </td>
                                  <td className="p-2">
                                    <Button variant="ghost" size="icon-xs" onClick={() => removeWatch(name)}>
                                      <Trash2 className="size-3" />
                                    </Button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </ScrollArea>
                      ) : (
                        <p className="text-sm text-muted-foreground p-4 border text-center">
                          No watches yet. Use search to find addresses, then add them as watches.
                        </p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {step === 3 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Target className="size-5" />
                      Reward Signals
                    </CardTitle>
                    <CardDescription>
                      Define how memory values translate to rewards for the RL agent
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Add reward */}
                    <div className="space-y-3">
                      <h4 className="font-medium">Add Reward</h4>
                      <div className="grid grid-cols-4 gap-2">
                        <Select value={rewardVariable} onValueChange={setRewardVariable}>
                          <SelectTrigger>
                            <SelectValue placeholder="Variable" />
                          </SelectTrigger>
                          <SelectContent>
                            {Object.keys(watches).map(name => (
                              <SelectItem key={name} value={name}>{name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Select value={rewardOperation} onValueChange={setRewardOperation}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="delta">Delta (change)</SelectItem>
                            <SelectItem value="threshold">Threshold</SelectItem>
                            <SelectItem value="equals">Equals</SelectItem>
                          </SelectContent>
                        </Select>
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="Multiplier"
                          value={rewardMultiplier}
                          onChange={(e) => setRewardMultiplier(e.target.value)}
                        />
                        <Button onClick={handleAddReward}>
                          <Plus className="size-4 mr-2" />
                          Add
                        </Button>
                      </div>
                      {Object.keys(watches).length === 0 && (
                        <p className="text-sm text-muted-foreground">
                          Add memory watches in Step 2 first, then define rewards based on them.
                        </p>
                      )}
                    </div>

                    <Separator />

                    {/* Done conditions */}
                    <div className="space-y-3">
                      <h4 className="font-medium">Done Condition</h4>
                      <p className="text-sm text-muted-foreground">
                        When should the episode end?
                      </p>
                      <div className="grid grid-cols-4 gap-2">
                        <Select value={doneVariable} onValueChange={setDoneVariable}>
                          <SelectTrigger>
                            <SelectValue placeholder="Variable" />
                          </SelectTrigger>
                          <SelectContent>
                            {Object.keys(watches).map(name => (
                              <SelectItem key={name} value={name}>{name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Select value={doneOperation} onValueChange={setDoneOperation}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="equal">Equals</SelectItem>
                            <SelectItem value="less-than">Less Than</SelectItem>
                            <SelectItem value="greater-than">Greater Than</SelectItem>
                          </SelectContent>
                        </Select>
                        <Input
                          type="number"
                          placeholder="Reference"
                          value={doneReference}
                          onChange={(e) => setDoneReference(e.target.value)}
                        />
                        <Button onClick={handleAddDone}>
                          <Plus className="size-4 mr-2" />
                          Add
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {step === 4 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Flag className="size-5" />
                      Save States
                    </CardTitle>
                    <CardDescription>
                      Create save states for training starting points
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Game Controls */}
                    <div className="flex items-center gap-2 p-3 bg-muted">
                      <Button
                        variant={isPlaying ? "destructive" : "default"}
                        size="sm"
                        onClick={isPlaying ? stopPlaying : startPlaying}
                      >
                        {isPlaying ? (
                          <><Pause className="size-4 mr-2" />Pause</>
                        ) : (
                          <><Play className="size-4 mr-2" />Play</>
                        )}
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => stepFrames(60)}>
                        <SkipForward className="size-4 mr-2" />
                        +60 frames
                      </Button>
                      <div className="flex-1" />
                      <span className="text-sm text-muted-foreground">
                        Frame: {frameCount.toLocaleString()}
                      </span>
                    </div>

                    <p className="text-sm text-muted-foreground">
                      Play to an interesting point (start of level, before boss, etc.) and save a state.
                      Training can start from any of these states.
                    </p>

                    {/* Save state form */}
                    <div className="flex gap-2">
                      <Input
                        placeholder="State name (e.g. Start, Level2)"
                        value={stateName}
                        onChange={(e) => setStateName(e.target.value)}
                      />
                      <Button onClick={handleSaveState} disabled={!stateName}>
                        <Save className="size-4 mr-2" />
                        Save State
                      </Button>
                    </div>

                    {/* Saved states list */}
                    <div className="space-y-2">
                      {savedStates.map((state) => (
                        <div
                          key={state.name}
                          className="flex items-center justify-between p-3 border"
                        >
                          <div>
                            <p className="font-medium">{state.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {(state.size / 1024).toFixed(1)} KB
                            </p>
                          </div>
                          <Button variant="outline" size="sm" onClick={() => loadState(state.name)}>
                            <Eye className="size-4 mr-2" />
                            Load
                          </Button>
                        </div>
                      ))}
                      {savedStates.length === 0 && (
                        <p className="text-sm text-muted-foreground p-4 border text-center">
                          No states saved yet. Play the game and save states at interesting points.
                        </p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Game Preview */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Game Preview</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="aspect-4/3 bg-muted flex items-center justify-center overflow-hidden">
                    {screenImage ? (
                      <img
                        src={screenImage}
                        alt="Game screen"
                        className="w-full h-full object-contain"
                        style={{ imageRendering: "pixelated" }}
                      />
                    ) : (
                      <div className="text-center text-muted-foreground">
                        <Gamepad2 className="size-8 mx-auto mb-2" />
                        <p className="text-xs">No frame yet</p>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 mt-2">
                    <Button variant="outline" size="sm" className="flex-1" onClick={refreshScreen}>
                      Refresh
                    </Button>
                    <Button
                      variant={isPlaying ? "destructive" : "default"}
                      size="sm"
                      className="flex-1"
                      onClick={isPlaying ? stopPlaying : startPlaying}
                    >
                      {isPlaying ? "Pause" : "Play"}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Generated Files Preview */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Generated Files</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <FileCode className="size-4 text-muted-foreground" />
                    <span className="font-mono">data.json</span>
                    <Badge variant="outline" className="ml-auto text-xs">
                      {Object.keys(watches).length} vars
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <FileCode className="size-4 text-muted-foreground" />
                    <span className="font-mono">scenario.json</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <FileCode className="size-4 text-muted-foreground" />
                    <span className="font-mono">metadata.json</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <FileCode className="size-4 text-muted-foreground" />
                    <span className="font-mono">rom.sha</span>
                  </div>
                  {savedStates.map((s) => (
                    <div key={s.name} className="flex items-center gap-2">
                      <FileCode className="size-4 text-muted-foreground" />
                      <span className="font-mono">{s.name}.state</span>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Actions */}
              <Card>
                <CardContent className="pt-6 space-y-2">
                  <Button
                    className="w-full"
                    onClick={handleExport}
                    disabled={Object.keys(watches).length === 0}
                  >
                    <Download className="size-4 mr-2" />
                    Export Connector
                  </Button>
                  <p className="text-xs text-muted-foreground text-center">
                    {Object.keys(watches).length === 0
                      ? "Add at least one memory watch to export"
                      : "Export will register the connector and link it to this ROM"}
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </PageContent>
    </Page>
  )
}
