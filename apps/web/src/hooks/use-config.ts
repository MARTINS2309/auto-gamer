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
  const { data: config, isLoading, dataUpdatedAt } = useConfig()
  const updateConfig = useUpdateConfig()
  const [localOverrides, setLocalOverrides] = useState<ConfigUpdate>({})
  const [lastSyncedAt, setLastSyncedAt] = useState(0)

  // Derive form data: use server data unless user has made local changes
  const formData = useMemo(() => {
    // If server data is newer than our last sync, reset to server data
    if (dataUpdatedAt > lastSyncedAt && config) {
      return config
    }
    // Otherwise merge local overrides with server data
    return { ...config, ...localOverrides }
  }, [config, localOverrides, dataUpdatedAt, lastSyncedAt])

  const isDirty = Object.keys(localOverrides).length > 0

  const handleChange = useCallback(<K extends keyof Config>(key: K, value: Config[K]) => {
    setLocalOverrides((prev) => ({ ...prev, [key]: value }))
  }, [])

  const handleSave = useCallback(() => {
    updateConfig.mutate(formData as Config, {
      onSuccess: () => {
        setLocalOverrides({})
        setLastSyncedAt(Date.now())
      },
    })
  }, [updateConfig, formData])

  const handleReset = useCallback(() => {
    setLocalOverrides({})
    setLastSyncedAt(Date.now())
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
