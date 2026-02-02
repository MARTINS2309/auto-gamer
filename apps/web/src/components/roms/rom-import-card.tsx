import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { FolderInput } from "lucide-react"

interface RomImportCardProps {
  onImport: (path: string) => void
  isPending: boolean
}

export function RomImportCard({ onImport, isPending }: RomImportCardProps) {
  const [importPath, setImportPath] = useState("")

  const handleImport = () => {
    if (!importPath.trim()) return
    onImport(importPath.trim())
    setImportPath("")
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-2">
          <Input
            value={importPath}
            onChange={(e) => setImportPath(e.target.value)}
            placeholder="Path to ROM directory (e.g., /home/user/roms)"
            className="font-mono flex-1"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleImport()
            }}
          />
          <Button
            onClick={handleImport}
            disabled={isPending || !importPath.trim()}
          >
            <FolderInput className="size-4" />
            {isPending ? "Importing..." : "Import"}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
