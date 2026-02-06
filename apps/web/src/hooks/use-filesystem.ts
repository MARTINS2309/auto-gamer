import { useQuery, useMutation } from "@tanstack/react-query"
import { api } from "@/lib/api"

export const filesystemKeys = {
    all: ["filesystem"] as const,
    list: (path: string) => ["filesystem", "list", path] as const,
    home: ["filesystem", "home"] as const,
}

export function useFilesystemHome(enabled: boolean = true) {
    return useQuery({
        queryKey: filesystemKeys.home,
        queryFn: api.filesystem.home,
        enabled,
    })
}

export function useFilesystemList(path: string, showHidden: boolean = false, dirsOnly: boolean = true, enabled: boolean = true) {
    return useQuery({
        queryKey: filesystemKeys.list(path),
        queryFn: () => api.filesystem.list(path, showHidden, dirsOnly),
        enabled: enabled && !!path,
    })
}

export function useValidatePath() {
    return useMutation({
        mutationFn: (params: { path: string; mustExist?: boolean; mustBeDir?: boolean }) =>
            api.filesystem.validate(params.path, params.mustExist, params.mustBeDir),
        onError: (error) => {
            console.error("Path validation failed:", error)
        },
    })
}
