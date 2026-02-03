import { ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import type { Run } from "@/lib/schemas"

interface RunConfigurationProps {
    run: Run
}

export function RunConfiguration({ run }: RunConfigurationProps) {
    const config = {
        rom: run.rom,
        state: run.state,
        algorithm: run.algorithm,
        hyperparams: run.hyperparams,
        max_steps: run.max_steps,
        n_envs: run.n_envs,
        created_at: run.created_at,
        started_at: run.started_at,
    }

    return (
        <Collapsible>
            <CollapsibleTrigger asChild>
                <Button variant="ghost" className="w-full justify-between">
                    Configuration
                    <ChevronDown className="size-4" />
                </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
                <Card className="mt-2">
                    <CardContent className="pt-6">
                        <pre className="text-xs font-mono overflow-auto max-h-[400px]">
                            {JSON.stringify(config, null, 2)}
                        </pre>
                    </CardContent>
                </Card>
            </CollapsibleContent>
        </Collapsible>
    )
}
