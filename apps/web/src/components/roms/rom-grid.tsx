import { useMemo } from "react"
import { Gamepad2 } from "lucide-react"
import { RomCard } from "./rom-card"
import { useGameMetadataBatch } from "@/hooks"
import type { Rom } from "@/lib/schemas"

interface RomGridProps {
  roms: Rom[]
  isLoading: boolean
  onSelectRom: (id: string) => void
}

export function RomGrid({ roms, isLoading, onSelectRom }: RomGridProps) {
  // Batch fetch metadata for all visible ROMs in ONE request
  // Use rom.id as the correlation key
  const batchRequest = useMemo(
    () => roms.map(rom => ({ game_id: rom.id, system: rom.system })),
    [roms]
  )
  const { metadataMap } = useGameMetadataBatch(batchRequest)

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
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
      {roms.map((rom) => (
        <RomCard
          key={rom.id}
          rom={rom}
          metadata={metadataMap.get(rom.id)}
          onSelect={() => onSelectRom(rom.id)}
        />
      ))}
    </div>
  )
}
