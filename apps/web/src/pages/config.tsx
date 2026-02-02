import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Save } from "lucide-react"
import { useEmulators, useConfigForm } from "@/hooks"

export function ConfigPage() {
  const { data: emulators = [] } = useEmulators()
  const { formData, isSaving, handleChange, handleSave } = useConfigForm()

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold">Configuration</h1>
        <p className="text-muted-foreground">Training defaults and settings</p>
      </div>

      {/* Supported Platforms */}
      <Card>
        <CardHeader>
          <CardTitle>Supported Platforms</CardTitle>
          <CardDescription>Available emulation cores via stable-retro</CardDescription>
        </CardHeader>
        <CardContent>
          {emulators.length === 0 ? (
            <p className="text-muted-foreground">No platforms available</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {emulators.map((platform) => (
                <Badge key={platform} variant="outline" className="text-base py-1 px-3">
                  {platform}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Training Defaults */}
      <Card>
        <CardHeader>
          <CardTitle>Training Defaults</CardTitle>
          <CardDescription>Default settings for new training runs</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label>Algorithm</Label>
              <Select
                value={formData.default_algorithm}
                onValueChange={(v) => handleChange("default_algorithm", v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select algorithm" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PPO">PPO</SelectItem>
                  <SelectItem value="A2C">A2C</SelectItem>
                  <SelectItem value="DQN">DQN</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Device</Label>
              <Select
                value={formData.default_device}
                onValueChange={(v) => handleChange("default_device", v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select device" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="cuda">CUDA (GPU)</SelectItem>
                  <SelectItem value="cpu">CPU</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Storage Path</Label>
            <Input
              value={formData.storage_path || ""}
              onChange={(e) => handleChange("storage_path", e.target.value)}
              placeholder="./data"
              className="font-mono"
            />
            <p className="text-sm text-muted-foreground">
              Directory for checkpoints and training data
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={isSaving}>
          <Save className="size-4" />
          {isSaving ? "Saving..." : "Save Changes"}
        </Button>
      </div>
    </div>
  )
}
