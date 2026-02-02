import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"

export const romKeys = {
  all: ["roms"] as const,
  detail: (id: string) => ["rom", id] as const,
  states: (id: string) => ["rom", id, "states"] as const,
}

export function useRoms() {
  return useQuery({
    queryKey: romKeys.all,
    queryFn: api.roms.list,
  })
}

export function useRom(id: string | null) {
  return useQuery({
    queryKey: romKeys.detail(id!),
    queryFn: () => api.roms.get(id!),
    enabled: !!id,
  })
}

export function useRomStates(id: string | null) {
  return useQuery({
    queryKey: romKeys.states(id!),
    queryFn: () => api.roms.getStates(id!),
    enabled: !!id,
  })
}

export function useImportRoms() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.roms.import,
    onSuccess: (result) => {
      toast.success(`Imported ${result.imported} ROMs`)
      queryClient.invalidateQueries({ queryKey: romKeys.all })
    },
    onError: (error) => {
      toast.error(`Import failed: ${error.message}`)
    },
  })
}
