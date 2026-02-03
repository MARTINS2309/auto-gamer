import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { LabelWithTooltip } from "./common"
import type { ConfigUpdate } from "@/lib/schemas"

interface SystemSettingsCardProps {
    formData: ConfigUpdate
    emulators: string[]
    onChange: (field: keyof ConfigUpdate, value: any) => void
}

export function SystemSettingsCard({ formData, emulators, onChange }: SystemSettingsCardProps) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
                <h3 className="text-lg font-medium mb-1">System</h3>
                <p className="text-sm text-muted-foreground">Core engine configuration and paths.</p>
            </div>
            <Card className="lg:col-span-2">
                <CardContent className="space-y-6 pt-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <LabelWithTooltip tooltip="Preferred hardware acceleration. CUDA requires NVIDIA GPU drivers.">
                                Compute Device
                            </LabelWithTooltip>
                            <Select
                                value={formData.default_device}
                                onValueChange={(v) => onChange("default_device", v)}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="auto">Auto (Detect)</SelectItem>
                                    <SelectItem value="cuda">CUDA (NVIDIA/ROCm)</SelectItem>
                                    <SelectItem value="mps">MPS (Apple Silicon)</SelectItem>
                                    <SelectItem value="cpu">CPU (Slower)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <LabelWithTooltip tooltip="Maximum number of simultaneous training runs. Increasing this puts heavy load on CPU/RAM.">
                                Max Concurrent Runs
                            </LabelWithTooltip>
                            <Input
                                type="number"
                                min={1}
                                max={16}
                                value={formData.max_concurrent_runs}
                                onChange={(e) => onChange("max_concurrent_runs", Math.max(1, parseInt(e.target.value) || 1))}
                            />
                        </div>
                    </div>

                    <Separator />

                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Absolute path on the server where training data, logs, and checkpoints are stored.">
                            Data Storage Path
                        </LabelWithTooltip>
                        <Input
                            value={formData.storage_path}
                            onChange={(e) => onChange("storage_path", e.target.value)}
                            className="font-mono text-sm"
                        />
                    </div>

                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Directory to automatically scan for new ROM files on startup or when requested.">
                            ROMs Import Path
                        </LabelWithTooltip>
                        <Input
                            value={formData.roms_path || ""}
                            onChange={(e) => onChange("roms_path", e.target.value)}
                            placeholder="/home/user/games"
                            className="font-mono text-sm"
                        />
                    </div>

                    <div className="pt-2">
                        <Label className="mb-2 block">Installed Cores</Label>
                        <div className="flex flex-wrap gap-2">
                            {emulators.length > 0 ? (
                                emulators.map(e => <Badge key={e} variant="secondary">{e}</Badge>)
                            ) : (
                                <span className="text-muted-foreground text-sm">No stable-retro cores found.</span>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
