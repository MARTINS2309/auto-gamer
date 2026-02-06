import { useState, useEffect } from "react"
import { Folder, FolderOpen, ChevronRight, Home, ArrowUp, Loader2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { useFilesystemHome, useFilesystemList } from "@/hooks/use-filesystem"

interface DirectoryPickerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (path: string) => void
  title?: string
  description?: string
  initialPath?: string
}

export function DirectoryPickerDialog({
  open,
  onOpenChange,
  onSelect,
  title = "Select Directory",
  description = "Browse and select a directory",
  initialPath,
}: DirectoryPickerDialogProps) {
  const [currentPath, setCurrentPath] = useState<string>("~")
  const [manualPath, setManualPath] = useState<string>("")

  // Fetch home directory on mount
  const { data: homeData } = useFilesystemHome(open)

  // Fetch directory listing
  const {
    data: dirData,
    isLoading,
    error,
    refetch,
  } = useFilesystemList(currentPath, false, true, open)

  // Initialize path when dialog opens
  useEffect(() => {
    if (!open) return

    if (initialPath) {
      setCurrentPath(initialPath)
      setManualPath(initialPath)
    } else if (homeData?.path && currentPath === "~") {
      setCurrentPath(homeData.path)
      setManualPath(homeData.path)
    }
  }, [open, initialPath, homeData?.path, currentPath])

  // Update manual path input when directory changes
  useEffect(() => {
    if (dirData?.path && dirData.path !== manualPath) {
      setManualPath(dirData.path)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dirData?.path])

  const handleNavigate = (path: string) => {
    setCurrentPath(path)
  }

  const handleGoUp = () => {
    if (dirData?.parent) {
      setCurrentPath(dirData.parent)
    }
  }

  const handleGoHome = () => {
    if (homeData?.path) {
      setCurrentPath(homeData.path)
    }
  }

  const handleManualPathSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (manualPath.trim()) {
      setCurrentPath(manualPath.trim())
    }
  }

  const handleSelect = () => {
    if (dirData?.path) {
      onSelect(dirData.path)
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Path input */}
          <form onSubmit={handleManualPathSubmit} className="flex gap-2">
            <Input
              value={manualPath}
              onChange={(e) => setManualPath(e.target.value)}
              placeholder="/path/to/directory"
              className="font-mono text-sm"
            />
            <Button type="submit" variant="secondary" size="sm">
              Go
            </Button>
          </form>

          {/* Navigation bar */}
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleGoHome}
              disabled={!homeData?.path}
              title="Go to home directory"
            >
              <Home className="size-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleGoUp}
              disabled={!dirData?.parent}
              title="Go up one directory"
            >
              <ArrowUp className="size-4" />
            </Button>
            <div className="flex-1 text-sm text-muted-foreground font-mono truncate px-2">
              {dirData?.path || currentPath}
            </div>
          </div>

          {/* Directory listing */}
          <ScrollArea className="h-75 border rounded-md">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="size-6 animate-spin text-muted-foreground" />
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center h-full p-4 text-center">
                <p className="text-sm text-destructive">Failed to load directory</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {error instanceof Error ? error.message : "Unknown error"}
                </p>
                <Button variant="outline" size="sm" className="mt-2" onClick={() => refetch()}>
                  Retry
                </Button>
              </div>
            ) : dirData?.entries.length === 0 ? (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                No subdirectories
              </div>
            ) : (
              <div className="p-1">
                {dirData?.entries.map((entry) => (
                  <button
                    key={entry.path}
                    onClick={() => handleNavigate(entry.path)}
                    disabled={!entry.is_readable}
                    className={cn(
                      "w-full flex items-center gap-2 px-2 py-1.5 rounded-sm text-sm text-left",
                      "hover:bg-accent hover:text-accent-foreground",
                      "focus:bg-accent focus:text-accent-foreground focus:outline-none",
                      !entry.is_readable && "opacity-50 cursor-not-allowed"
                    )}
                  >
                    <Folder className="size-4 text-muted-foreground shrink-0" />
                    <span className="truncate flex-1">{entry.name}</span>
                    <ChevronRight className="size-4 text-muted-foreground shrink-0" />
                  </button>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSelect} disabled={!dirData?.path}>
            <FolderOpen className="size-4 mr-2" />
            Select This Directory
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
