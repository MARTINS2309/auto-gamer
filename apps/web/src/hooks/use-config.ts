import { useState, useCallback, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { Config, ConfigUpdate } from "@/lib/schemas"
import { toast } from "sonner"

export const configKeys = {
  config: ["config"] as const,
  emulators: ["emulators"] as const,
}

export function useConfig() {
  return useQuery({
    queryKey: configKeys.config,
    queryFn: api.config.get,
  })
}

export function useEmulators() {
  return useQuery({
    queryKey: configKeys.emulators,
    queryFn: api.emulators.list,
  })
}

export function useUpdateConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.config.update,
    onSuccess: () => {
      toast.success("Config saved")
      queryClient.invalidateQueries({ queryKey: configKeys.config })
    },
    onError: (error) => {
      toast.error(`Failed to save: ${error.message}`)
    },
  })
}

// =============================================================================
// Form State Hook
// =============================================================================

export function useConfigForm() {
  const { data: config, isLoading } = useConfig()
  const updateConfig = useUpdateConfig()
  const [localOverrides, setLocalOverrides] = useState<ConfigUpdate>({})

  // Derive form data: merge local overrides with server data
  const formData = useMemo(() => {
    if (!config) return (localOverrides as Config) || {}
    return { ...config, ...localOverrides }
  }, [config, localOverrides])

  const isDirty = useMemo(() => Object.keys(localOverrides).length > 0, [localOverrides])

  const handleChange = useCallback(<K extends keyof Config>(key: K, value: Config[K]) => {
    setLocalOverrides((prev) => ({ ...prev, [key]: value }))
  }, [])

  const handleSave = useCallback(() => {
    if (!config) return
    // Ensure we send complete config
    const merged = { ...config, ...localOverrides }
    updateConfig.mutate(merged, {
      onSuccess: () => {
        setLocalOverrides({})
      },
    })
  }, [updateConfig, config, localOverrides])

  const handleReset = useCallback(() => {
    setLocalOverrides({})
  }, [])

  return {
    formData,
    isLoading,
    isDirty,
    isSaving: updateConfig.isPending,
    handleChange,
    handleSave,
    handleReset,
  }
}
