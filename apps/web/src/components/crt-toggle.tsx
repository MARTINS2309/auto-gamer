
import { Button } from "@/components/ui/button"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { LucideMonitor, LucideMonitorDown } from "lucide-react"
import { useEffect, useState } from "react"

export function CRTToggle() {
    const [enabled, setEnabled] = useState(false)

    useEffect(() => {
        if (enabled) {
            document.body.classList.add("crt-enabled")
        } else {
            document.body.classList.remove("crt-enabled")
        }
    }, [enabled])

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setEnabled(!enabled)}
                    aria-pressed={enabled}
                    className={enabled ? "bg-accent text-accent-foreground" : ""}
                >
                    {enabled ? (
                        <LucideMonitorDown className="h-[1.2rem] w-[1.2rem]" />
                    ) : (
                        <LucideMonitor className="h-[1.2rem] w-[1.2rem]" />
                    )}
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setEnabled(true)}>
                    Enable CRT Effect
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setEnabled(false)}>
                    Disable CRT Effect
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    )
}