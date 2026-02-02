import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Play } from "lucide-react"
import type { Rom } from "@/lib/schemas"

interface RomCardProps {
  rom: Rom
  onSelect: () => void
}

export function RomCard({ rom, onSelect }: RomCardProps) {
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
          <Button
            size="sm"
            onClick={(e) => {
              e.stopPropagation()
              onSelect()
            }}
          >
            <Play className="size-3" />
            Train
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
