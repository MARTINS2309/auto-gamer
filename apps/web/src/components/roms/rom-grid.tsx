import { useState, useEffect, useRef } from "react"
import { Gamepad2 } from "lucide-react"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import { RomCard } from "./rom-card"
import type { RomListItem } from "@/lib/schemas"

const PAGE_SIZE = 24

interface RomGridProps {
  roms: RomListItem[]
  isLoading: boolean
  onSelectRom: (id: string) => void
}

/** Generate page numbers to display with ellipsis */
function getPageNumbers(current: number, total: number): (number | "ellipsis")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i)
  }

  const pages: (number | "ellipsis")[] = []

  // Always show first page
  pages.push(0)

  if (current > 2) {
    pages.push("ellipsis")
  }

  // Show pages around current
  for (let i = Math.max(1, current - 1); i <= Math.min(total - 2, current + 1); i++) {
    pages.push(i)
  }

  if (current < total - 3) {
    pages.push("ellipsis")
  }

  // Always show last page
  pages.push(total - 1)

  return pages
}

export function RomGrid({ roms, isLoading, onSelectRom }: RomGridProps) {
  const [page, setPage] = useState(0)
  const gridRef = useRef<HTMLDivElement>(null)
  const [prevRomsLength, setPrevRomsLength] = useState(roms.length)

  // Reset to first page when roms list changes (render-time state adjustment)
  if (prevRomsLength !== roms.length) {
    setPrevRomsLength(roms.length)
    setPage(0)
  }

  // Scroll to top of grid when page changes
  useEffect(() => {
    gridRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }, [page])

  const totalPages = Math.ceil(roms.length / PAGE_SIZE)
  const startIndex = page * PAGE_SIZE
  const endIndex = startIndex + PAGE_SIZE
  const visibleRoms = roms.slice(startIndex, endIndex)

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

  const pageNumbers = getPageNumbers(page, totalPages)

  return (
    <div ref={gridRef} className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {visibleRoms.map((rom) => (
          <RomCard
            key={rom.id}
            rom={rom}
            onSelect={() => onSelectRom(rom.id)}
          />
        ))}
      </div>

      {totalPages > 1 && (
        <Pagination className="pt-4">
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                className={page === 0 ? "pointer-events-none opacity-50" : "cursor-pointer"}
              />
            </PaginationItem>

            {pageNumbers.map((p, i) =>
              p === "ellipsis" ? (
                <PaginationItem key={`ellipsis-${i}`}>
                  <PaginationEllipsis />
                </PaginationItem>
              ) : (
                <PaginationItem key={p}>
                  <PaginationLink
                    isActive={p === page}
                    onClick={() => setPage(p)}
                    className="cursor-pointer"
                  >
                    {p + 1}
                  </PaginationLink>
                </PaginationItem>
              )
            )}

            <PaginationItem>
              <PaginationNext
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                className={page >= totalPages - 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </div>
  )
}
