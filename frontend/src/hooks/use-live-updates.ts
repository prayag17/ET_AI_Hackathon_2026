/**
 * useLiveUpdates — keeps the dashboard current without manual reloads
 * (issue #45).
 *
 * Opens a WebSocket to the backend's /maps/ws channel; when the server
 * announces that the underlying data changed, the pollution / forecast /
 * advisory queries are invalidated so TanStack Query refetches them and the
 * map, timeline, and AI advisor all refresh in place. Reconnects with
 * exponential backoff if the backend goes away.
 */

import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

const LIVE_QUERY_KEYS = ['pollution', 'forecast', 'advisory']
const MAX_BACKOFF_MS = 30_000

/** Returns whether the live channel is currently connected. */
export function useLiveUpdates(): boolean {
  const queryClient = useQueryClient()
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let ws: WebSocket | null = null
    let retryTimer: ReturnType<typeof setTimeout> | null = null
    let attempts = 0
    let disposed = false

    const connect = () => {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${window.location.host}/api/maps/ws`)

      ws.onopen = () => {
        attempts = 0
        setConnected(true)
      }
      ws.onmessage = (event: MessageEvent<string>) => {
        let message: { type?: string }
        try {
          message = JSON.parse(event.data) as { type?: string }
        } catch {
          return
        }
        if (message.type === 'data_updated') {
          for (const key of LIVE_QUERY_KEYS) {
            void queryClient.invalidateQueries({ queryKey: [key] })
          }
        }
      }
      ws.onclose = () => {
        if (disposed) return
        setConnected(false)
        retryTimer = setTimeout(
          connect,
          Math.min(MAX_BACKOFF_MS, 1000 * 2 ** attempts++),
        )
      }
    }

    connect()
    return () => {
      disposed = true
      if (retryTimer) clearTimeout(retryTimer)
      ws?.close()
    }
  }, [queryClient])

  return connected
}
