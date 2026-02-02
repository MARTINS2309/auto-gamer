import { Gamepad2 } from "lucide-react"
import { RomCard } from "./rom-card"
import type { Rom } from "@/lib/schemas"

interface RomGridProps {
  roms: Rom[]
  isLoading: boolean
  onSelectRom: (id: string) => void
}

export function RomGrid({ roms, isLoading, onSelectRom }: RomGridProps) {
  if (isLoading) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        Loading ROMs...
      </div>
    )
  }

  if (roms.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Gamepad2 className="size-12 mx-auto mb-4 opacity-50" />
        <p className="text-lg">No ROMs found</p>
        <p className="text-sm">Import ROMs using the path input above</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 stagger-children">
      {roms.map((rom) => (
        <RomCard
          key={rom.id}
          rom={rom}
          onSelect={() => onSelectRom(rom.id)}
        />
      ))}
    </div>
  )
}
