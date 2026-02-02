import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface StatCardProps {
  title: string
  value: string | number
  icon: React.ElementType
  color?: string
  subValue?: string
}

export function StatCard({ title, value, icon: Icon, color, subValue }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-mono-sm tracking-stat text-muted-foreground flex items-center gap-2">
          <Icon className={`size-4 ${color || ""}`} />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className={`text-3xl font-semibold ${color || ""}`}>{value}</p>
        {subValue && <p className="text-xs text-muted-foreground">{subValue}</p>}
      </CardContent>
    </Card>
  )
}

// Compact stat tile variant (used in run detail)
interface StatTileProps {
  label: string
  value: string | number
  subValue?: string
  icon: React.ElementType
  color?: string
}

export function StatTile({ label, value, subValue, icon: Icon, color }: StatTileProps) {
  return (
    <div className="flex items-center gap-3 p-4 border">
      <Icon className={`size-5 ${color || "text-muted-foreground"}`} />
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-wider">{label}</p>
        <p className={`text-xl font-semibold ${color || ""}`}>{value}</p>
        {subValue && <p className="text-xs text-muted-foreground">{subValue}</p>}
      </div>
    </div>
  )
}
