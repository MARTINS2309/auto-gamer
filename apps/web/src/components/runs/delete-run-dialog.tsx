import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { useDeleteRun } from "@/hooks"

interface DeleteRunDialogProps {
    runId: string
    open: boolean
    onOpenChange: (open: boolean) => void
}

export function DeleteRunDialog({ runId, open, onOpenChange }: DeleteRunDialogProps) {
    const deleteRun = useDeleteRun()

    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Delete this run?</AlertDialogTitle>
                    <AlertDialogDescription>
                        This action cannot be undone. All run data including logs, metrics, and checkpoints will be permanently deleted.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        onClick={() => deleteRun.mutate(runId)}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                        {deleteRun.isPending ? "Deleting..." : "Delete"}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    )
}
