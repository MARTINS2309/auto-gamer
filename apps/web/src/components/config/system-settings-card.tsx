import { useState } from "react"
import { FolderOpen } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DirectoryPickerDialog } from "@/components/ui/directory-picker-dialog"
import { LabelWithTooltip } from "./common"
import type { ConfigUpdate } from "@/lib/schemas"

interface SystemSettingsCardProps {
    formData: ConfigUpdate
    emulators: string[]
    onChange: (field: keyof ConfigUpdate, value: ConfigUpdate[keyof ConfigUpdate]) => void
}

export function SystemSettingsCard({ formData, emulators, onChange }: SystemSettingsCardProps) {
    const [pickerOpen, setPickerOpen] = useState(false)
    const [recordingPickerOpen, setRecordingPickerOpen] = useState(false)

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
                            <LabelWithTooltip tooltip="Preferred hardware acceleration. Supports CUDA (NVIDIA), ROCm (AMD), and MPS (Apple Silicon).">
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
                                    <SelectItem value="cuda">CUDA / ROCm (NVIDIA/AMD)</SelectItem>
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
                        <div className="flex gap-1">
                            <Input
                                value={formData.storage_path}
                                onChange={(e) => onChange("storage_path", e.target.value)}
                                className="font-mono text-sm"
                            />
                            <Button
                                variant="outline"
                                size="icon"
                                onClick={() => setPickerOpen(true)}
                                title="Browse directories"
                            >
                                <FolderOpen className="size-4" />
                            </Button>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <LabelWithTooltip tooltip="Directory to save BK2 recording files (gameplay movies). If running on same machine as client.">
                            Recording Path
                        </LabelWithTooltip>
                        <div className="flex gap-1">
                            <Input
                                value={formData.recording_path || ""}
                                placeholder="(Optional) Default to current directory"
                                onChange={(e) => onChange("recording_path", e.target.value)}
                                className="font-mono text-sm"
                            />
                            <Button
                                variant="outline"
                                size="icon"
                                onClick={() => setRecordingPickerOpen(true)}
                                title="Browse directories"
                            >
                                <FolderOpen className="size-4" />
                            </Button>
                        </div>
                    </div>

                    <DirectoryPickerDialog
                        open={pickerOpen}
                        onOpenChange={setPickerOpen}
                        onSelect={(path) => onChange("storage_path", path)}
                        title="Select Storage Directory"
                        description="Browse to the directory where training data will be stored."
                        initialPath={formData.storage_path || undefined}
                    />

                    <DirectoryPickerDialog
                        open={recordingPickerOpen}
                        onOpenChange={setRecordingPickerOpen}
                        onSelect={(path) => onChange("recording_path", path)}
                        title="Select Recording Directory"
                        description="Browse to the directory where gameplay recordings will be saved."
                        initialPath={formData.recording_path || undefined}
                    />

                    <Separator />

                    <div className="space-y-1">
                        <h4 className="text-sm font-medium">IGDB API</h4>
                        <p className="text-xs text-muted-foreground">
                            Optional. Used to fetch game cover art and metadata. Get credentials at{" "}
                            <a href="https://dev.twitch.tv/console" target="_blank" rel="noopener noreferrer" className="underline text-primary">
                                dev.twitch.tv/console
                            </a>
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <Label>Client ID</Label>
                            <Input
                                value={formData.igdb_client_id || ""}
                                onChange={(e) => onChange("igdb_client_id", e.target.value || null)}
                                placeholder="Twitch Client ID"
                                className="font-mono text-sm"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Client Secret</Label>
                            <Input
                                type="password"
                                value={formData.igdb_client_secret || ""}
                                onChange={(e) => onChange("igdb_client_secret", e.target.value || null)}
                                placeholder="Twitch Client Secret"
                                className="font-mono text-sm"
                            />
                        </div>
                    </div>

                    <Separator />

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
