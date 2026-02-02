import { useState, useEffect, useCallback } from "react"
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
  const [formData, setFormData] = useState<ConfigUpdate>({})
  const [isDirty, setIsDirty] = useState(false)

  // Sync form data with loaded config
  useEffect(() => {
    if (config) {
      setFormData(config)
      setIsDirty(false)
    }
  }, [config])

  const handleChange = useCallback(<K extends keyof Config>(key: K, value: Config[K]) => {
    setFormData((prev) => ({ ...prev, [key]: value }))
    setIsDirty(true)
  }, [])

  const handleSave = useCallback(() => {
    updateConfig.mutate(formData as Config)
    setIsDirty(false)
  }, [updateConfig, formData])

  const handleReset = useCallback(() => {
    if (config) {
      setFormData(config)
      setIsDirty(false)
    }
  }, [config])

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
