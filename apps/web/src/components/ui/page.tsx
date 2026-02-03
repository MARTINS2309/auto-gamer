import * as React from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

function Page({ className, children, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="page"
      className={cn("flex h-full flex-col overflow-hidden", className)}
      {...props}
    >
      {children}
    </div>
  )
}

function PageHeader({ className, children, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="page-header"
      className={cn(
        "flex flex-shrink-0 flex-col gap-1 border-b bg-background px-6 py-4",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

function PageTitle({ className, ...props }: React.ComponentProps<"h1">) {
  return (
    <h1
      data-slot="page-title"
      className={cn("text-2xl font-semibold", className)}
      {...props}
    />
  )
}

function PageDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="page-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  )
}

function PageActions({ className, children, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="page-actions"
      className={cn("flex items-center gap-2", className)}
      {...props}
    >
      {children}
    </div>
  )
}

function PageContent({ className, children, ...props }: React.ComponentProps<"div">) {
  return (
    <ScrollArea className="flex-1">
      <div
        data-slot="page-content"
        className={cn("p-6", className)}
        {...props}
      >
        {children}
      </div>
    </ScrollArea>
  )
}

export { Page, PageHeader, PageTitle, PageDescription, PageActions, PageContent }
