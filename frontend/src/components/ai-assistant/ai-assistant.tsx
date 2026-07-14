import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import {
  AlertTriangle,
  CircleAlert,
  Clock,
  HeartPulse,
  MapPin,
  ShieldCheck,
  Sparkles,
  Wind,
} from 'lucide-react'
import { getAdvisory } from '@/lib/api'
import type { Recommendation } from '@/lib/api'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import StarBorder from '@/components/StarBorder'
import SpotlightCard from '@/components/SpotlightCard'
import CountUp from '@/components/CountUp'
import Strands from '@/components/Strands'
import GlassSurface from '@/components/GlassSurface'
import { cn } from '@/lib/utils'

const PRIORITY_META: Record<
  string,
  { badge: 'destructive' | 'default' | 'secondary'; icon: typeof AlertTriangle }
> = {
  high: { badge: 'destructive', icon: AlertTriangle },
  medium: { badge: 'default', icon: CircleAlert },
  low: { badge: 'secondary', icon: ShieldCheck },
}

/**
 * Floating trigger + glass overlay panel for the GRAP-Ahmedabad AI advisory
 * assistant. Fetches eagerly (not gated on open) so the trigger's badge can
 * surface a live recommendation count before the user ever opens the panel.
 */
export function AiAssistant() {
  const [open, setOpen] = useState(false)
  // The baseline "current status" card always exists, so count is never 0 —
  // track what's already been seen instead, so the badge clears once the
  // user has actually opened the panel and only reappears if the number
  // of advisories grows past that.
  const [seenCount, setSeenCount] = useState(0)
  const reducedMotion = useReducedMotion()

  const advisory = useQuery({
    queryKey: ['advisory'],
    queryFn: getAdvisory,
    staleTime: 5 * 60 * 1000,
  })

  const count = advisory.data?.advisories.length ?? 0
  const hasUnseen = count > seenCount

  const handleOpenChange = (next: boolean) => {
    setOpen(next)
    if (next) setSeenCount(count)
  }

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <div className="absolute bottom-6 left-6 z-20 size-14">
        <motion.div
          className="size-full"
          initial={reducedMotion ? false : { scale: 0, rotate: -160 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 260, damping: 18, delay: 0.2 }}
          whileHover={reducedMotion ? undefined : { scale: 1.08 }}
          whileTap={reducedMotion ? undefined : { scale: 0.92 }}
        >
          <PopoverTrigger asChild>
            <StarBorder
              color="var(--color-primary)"
              speed="4s"
              className="size-full shadow-lg"
              aria-label="Open AI advisory assistant"
            >
              <GlassSurface
                width="100%"
                height="100%"
                borderRadius={28}
                brightness={65}
                opacity={0.5}
                blur={8}
                className="text-primary"
              >
                <Sparkles className="size-5" />
              </GlassSurface>
            </StarBorder>
          </PopoverTrigger>
        </motion.div>

        <AnimatePresence>
          {hasUnseen && (
            <motion.div
              key={count}
              className="pointer-events-none absolute -right-1.5 -top-1.5 z-30"
              initial={reducedMotion ? false : { scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={reducedMotion ? undefined : { scale: 0, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 15 }}
            >
              <Badge className="h-5 min-w-5 justify-center border-2 border-background bg-destructive px-1 font-semibold text-white shadow-sm">
                {count}
              </Badge>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <PopoverContent
        side="top"
        align="start"
        sideOffset={16}
        className="w-[26rem] max-w-[calc(100vw-3rem)] rounded-3xl border-0 bg-transparent p-0 shadow-2xl ring-1 ring-foreground/10"
      >
        <div className="relative flex max-h-[min(32rem,70vh)] flex-col overflow-hidden rounded-3xl">
          <GlassSurface
            width="100%"
            height="100%"
            borderRadius={24}
            backgroundOpacity={0.55}
            brightness={55}
            blur={10}
            className="pointer-events-none absolute inset-0"
          />

          {/* Actual content sits above the glass layer, on solid cards
              where it matters, so readability never depends on exactly
              what's refracting underneath. */}
          <div className="relative z-10 flex min-h-0 flex-1 flex-col">
            <div className="flex items-center gap-2.5 p-4">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                <Wind className="size-4.5 text-primary" />
              </div>
              <div className="flex min-w-0 flex-col">
                <span className="text-base font-medium leading-tight">
                  AI Advisory Assistant
                </span>
                <span className="truncate text-xs text-muted-foreground">
                  GRAP-Ahmedabad · live 72h forecast
                </span>
              </div>
            </div>
            {/* Gradient hairline — quieter than a full border, still separates */}
            <div
              aria-hidden="true"
              className="h-px bg-gradient-to-r from-primary/50 via-border to-transparent"
            />

            {/* Native overflow scrolling — Radix ScrollArea never resolved
                a height inside this popover's flex chain, leaving the list
                unscrollable. A plain overflow div has no such dependency. */}
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
              <div className="flex flex-col gap-3 p-4">
                <AnimatePresence mode="wait">
                  {advisory.isPending && (
                    <motion.div
                      key="loading"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="relative flex h-40 flex-col items-center justify-center gap-3 overflow-hidden rounded-2xl border border-border bg-card"
                    >
                      {!reducedMotion && (
                        <div className="absolute inset-0 opacity-80">
                          <Strands
                            colors={[
                              '#38bdf8',
                              'var(--color-primary)',
                              '#38bdf8',
                            ]}
                            count={3}
                            speed={0.7}
                            thickness={0.6}
                            glow={2.2}
                          />
                        </div>
                      )}
                      <Wind className="relative size-6 text-primary" />
                      <p className="relative text-xs text-muted-foreground">
                        Consulting GRAP-Ahmedabad AI…
                      </p>
                    </motion.div>
                  )}

                  {advisory.isError && (
                    <motion.div
                      key="error"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      <Alert variant="destructive">
                        <AlertTitle>Couldn't load advisories</AlertTitle>
                        <AlertDescription className="flex flex-col items-start gap-2">
                          <span>Is the backend running?</span>
                          <Button size="sm" onClick={() => advisory.refetch()}>
                            Try again
                          </Button>
                        </AlertDescription>
                      </Alert>
                    </motion.div>
                  )}

                  {advisory.isSuccess && (
                    <motion.div
                      key="data"
                      className="flex flex-col gap-3"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      {advisory.data.advisories.map((rec, i) => (
                        <motion.div
                          key={`${rec.cell_id}-${i}`}
                          initial={
                            reducedMotion
                              ? false
                              : { opacity: 0, y: 24, scale: 0.94 }
                          }
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          transition={{
                            type: 'spring',
                            stiffness: 300,
                            damping: 24,
                            // Stagger only the first few — with hundreds of
                            // advisories an unbounded i*0.08 delays the tail
                            // by whole minutes
                            delay: reducedMotion ? 0 : Math.min(i, 6) * 0.08,
                          }}
                        >
                          <SpotlightCard
                            className="border-2"
                            style={{
                              borderColor: rec.stage_color ?? undefined,
                              // Faint wash of the stage color so the card
                              // reads as one tinted surface, not a bare
                              // box with a colored outline
                              backgroundImage: rec.stage_color
                                ? `linear-gradient(140deg, color-mix(in oklab, ${rec.stage_color} 9%, transparent), transparent 55%)`
                                : undefined,
                            }}
                          >
                            <RecommendationCard rec={rec} />
                          </SpotlightCard>
                        </motion.div>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}

function RecommendationCard({ rec }: { rec: Recommendation }) {
  const priority = rec.priority.toLowerCase()
  const meta = PRIORITY_META[priority] ?? PRIORITY_META.low
  const PriorityIcon = meta.icon
  const accent = rec.stage_color ?? 'var(--color-muted-foreground)'

  return (
    <div className="flex flex-col gap-3">
      {/* Eyebrow: what kind of card this is + priority */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span
            className={cn(
              'size-2 rounded-full',
              rec.is_baseline && 'animate-pulse',
            )}
            style={{ backgroundColor: accent }}
            aria-hidden="true"
          />
          <span
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: accent }}
          >
            {rec.is_baseline ? 'Live status' : rec.grap_stage}
          </span>
        </div>
        <Badge variant={meta.badge} className="gap-1">
          <PriorityIcon data-icon="inline-start" />
          {rec.priority}
        </Badge>
      </div>

      {/* Headline + supporting reason */}
      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold leading-snug text-foreground">
          {rec.action}
        </p>
        <p className="text-sm text-muted-foreground">{rec.reason}</p>
      </div>

      {/* Sensitive-groups health guidance */}
      {rec.citizen_advisory && rec.citizen_advisory.length > 0 && (
        <div className="flex gap-2 rounded-lg bg-muted/60 p-2.5">
          <HeartPulse className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
          <div className="flex flex-col gap-1">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              For sensitive groups
            </p>
            <ul className="flex flex-col gap-1 text-xs text-muted-foreground">
              {rec.citizen_advisory.map((tip) => (
                <li key={tip}>{tip}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Location + timing meta */}
      {!rec.is_baseline && (
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <MapPin className="size-3" />
            {rec.cell_id}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="size-3" />
            {rec.start_by}
          </span>
        </div>
      )}

      {/* Confidence meter */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
          Confidence
        </span>
        <Progress value={rec.confidence * 100} className="h-1.5 flex-1" />
        <span className="flex font-mono text-xs font-medium text-foreground">
          <CountUp to={Math.round(rec.confidence * 100)} duration={1} />%
        </span>
      </div>
    </div>
  )
}
