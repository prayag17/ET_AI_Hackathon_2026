import { Outlet, createRootRoute } from '@tanstack/react-router'


import '../styles.css'
import { ThemeProvider } from '@/components/theme-provider'
import { TooltipProvider } from '@/components/ui/tooltip'

export const Route = createRootRoute({
  component: RootComponent,
})

function RootComponent() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="et-ui-theme">
      <TooltipProvider>
        <Outlet />
      </TooltipProvider>

    </ThemeProvider>
  )
}
