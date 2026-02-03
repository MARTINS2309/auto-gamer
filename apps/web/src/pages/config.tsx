import { RotateCcw, Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Page, PageHeader, PageTitle, PageDescription, PageActions, PageContent } from "@/components/ui/page"
import { useEmulators, useConfigForm } from "@/hooks"
import { SystemSettingsCard } from "@/components/config/system-settings-card"
import { AlgorithmDefaultsCard } from "@/components/config/algorithm-defaults-card"
import { HyperparametersCard } from "@/components/config/hyperparameters-card"
export function ConfigPage() {
  const { data: emulators = [] } = useEmulators()
  const { formData, isSaving, isDirty, isLoading, handleChange, handleSave, handleReset } = useConfigForm()

  const hparams = formData.default_hyperparams || {}
  const algorithm = formData.default_algorithm || "PPO"

  const updateHParam = (key: string, val: number | boolean) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    handleChange("default_hyperparams", { ...hparams, [key]: val } as any)
  }

  if (isLoading) {
    return (
      <Page>
        <PageHeader><PageTitle>Loading Configuration...</PageTitle></PageHeader>
        <PageContent><div className="flex items-center justify-center p-8">Loading...</div></PageContent>
      </Page>
    )
  }

  return (
    <Page>
      <PageHeader className="flex-row items-center justify-between sticky top-0 bg-background/95 backdrop-blur z-10 py-4 border-b">
        <div>
          <PageTitle>Configuration</PageTitle>
          <PageDescription>Global settings and training defaults</PageDescription>
        </div>
        <PageActions className="flex items-center gap-2">
          {isDirty && (
            <Button variant="ghost" size="sm" onClick={handleReset}>
              <RotateCcw className="size-4 mr-2" />
              Reset
            </Button>
          )}
          <Button onClick={handleSave} disabled={isSaving || !isDirty}>
            <Save className="size-4 mr-2" />
            {isSaving ? "Saving..." : "Save Changes"}
          </Button>
        </PageActions>
      </PageHeader>

      <PageContent className="space-y-8 pb-20">

        {/* System Settings */}
        <SystemSettingsCard
          formData={formData}
          emulators={emulators}
          onChange={handleChange}
        />

        <Separator />

        {/* Algorithm Defaults */}
        <AlgorithmDefaultsCard
          formData={formData}
          onChange={handleChange}
        />

        <Separator />

        {/* Hyperparameters */}
        <HyperparametersCard
          algorithm={algorithm}
          hparams={hparams}
          onChange={updateHParam}
        />

      </PageContent>
    </Page>
  )
}
