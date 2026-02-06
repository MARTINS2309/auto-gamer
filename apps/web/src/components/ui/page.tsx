import * as React from "react"
import { useState, useEffect, useRef } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  NavigationMenu,
  NavigationMenuList,
  NavigationMenuItem,
} from "@/components/ui/navigation-menu"
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

interface PageHeaderProps extends React.ComponentProps<"header"> {
  hideOnScroll?: boolean
  scrollThreshold?: number
}

function PageHeader({
  className,
  children,
  hideOnScroll = true,
  scrollThreshold = 50,
  ...props
}: PageHeaderProps) {
  const [isVisible, setIsVisible] = useState(true)
  const [lastScrollY, setLastScrollY] = useState(0)
  const headerRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!hideOnScroll) return

    const scrollContainer = headerRef.current?.parentElement?.querySelector(
      '[data-slot="page-content"]'
    )?.querySelector('[data-radix-scroll-area-viewport]')

    if (!scrollContainer) return

    const handleScroll = () => {
      const currentScrollY = scrollContainer.scrollTop

      if (Math.abs(currentScrollY - lastScrollY) < scrollThreshold) {
        return
      }

      if (currentScrollY > lastScrollY && currentScrollY > 100) {
        setIsVisible(false)
      } else {
        setIsVisible(true)
      }

      setLastScrollY(currentScrollY)
    }

    scrollContainer.addEventListener("scroll", handleScroll, { passive: true })
    return () => scrollContainer.removeEventListener("scroll", handleScroll)
  }, [hideOnScroll, lastScrollY, scrollThreshold])

  return (
    <header
      ref={headerRef}
      data-slot="page-header"
      data-visible={isVisible}
      className={cn(
        "shrink-0 border-b bg-background/95 backdrop-blur-sm supports-backdrop-filter:bg-background/80 z-10 transition-transform duration-300",
        !isVisible && hideOnScroll && "-translate-y-full",
        className
      )}
      {...props}
    >
      {children}
    </header>
  )
}

function PageHeaderNav({ className, children, ...props }: React.ComponentProps<typeof NavigationMenu>) {
  return (
    <NavigationMenu
      data-slot="page-header-nav"
      className={cn("max-w-none justify-start px-6 py-3", className)}
      viewport={false}
      {...props}
    >
      <NavigationMenuList className="gap-4">
        {children}
      </NavigationMenuList>
    </NavigationMenu>
  )
}

function PageHeaderItem({ className, ...props }: React.ComponentProps<typeof NavigationMenuItem>) {
  return (
    <NavigationMenuItem
      data-slot="page-header-item"
      className={cn("", className)}
      {...props}
    />
  )
}

function PageTitle({ className, ...props }: React.ComponentProps<"h1">) {
  return (
    <h1
      data-slot="page-title"
      className={cn("text-xl font-semibold shrink-0", className)}
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

function PageToolbar({ className, children, ...props }: React.ComponentProps<typeof NavigationMenu>) {
  return (
    <NavigationMenu
      data-slot="page-toolbar"
      className={cn("max-w-none justify-start px-6 py-2 border-t", className)}
      viewport={false}
      {...props}
    >
      <NavigationMenuList className="gap-3 flex-wrap">
        {children}
      </NavigationMenuList>
    </NavigationMenu>
  )
}

function PageToolbarItem({ className, ...props }: React.ComponentProps<typeof NavigationMenuItem>) {
  return (
    <NavigationMenuItem
      data-slot="page-toolbar-item"
      className={cn("", className)}
      {...props}
    />
  )
}

function PageActions({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="page-actions"
      className={cn("flex items-center gap-2", className)}
      {...props}
    />
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

export {
  Page,
  PageHeader,
  PageHeaderNav,
  PageHeaderItem,
  PageTitle,
  PageDescription,
  PageActions,
  PageToolbar,
  PageToolbarItem,
  PageContent,
}
