import { MonitorOff } from "lucide-react"
import { Card } from "@/components/ui/card"
import { AspectRatio } from "@/components/ui/aspect-ratio"
import { NewRunDialog } from "@/components/runs/new-run-dialog"
import { Button } from "@/components/ui/button"

export function NoSignalHero() {
  return (
    <Card className="overflow-hidden p-0 crt-inset" style={{ backgroundColor: "#000" }}>
      <AspectRatio ratio={16 / 9} className="relative">
        {/* CRT scanline overlay */}
        <div
          className="absolute inset-0 pointer-events-none opacity-10"
          style={{
            background:
              "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.3) 2px, rgba(0,0,0,0.3) 4px)",
          }}
        />

        {/* Content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
          <MonitorOff className="size-16 text-muted-foreground opacity-50" />
          <p className="text-3xl text-muted-foreground animate-live tracking-widest">
            NO SIGNAL
          </p>
          <NewRunDialog
            trigger={
              <Button size="lg" className="mt-2">
                Start Training
              </Button>
            }
          />
        </div>
      </AspectRatio>
    </Card>
  )
}
