const listeners = new Set()
let socket = null
let reconnectTimer = null
let onlineListenerInstalled = false

function emit(event) {
  for (const listener of listeners) {
    try {
      listener(event)
    } catch {
      // noop
    }
  }
}

function toWsUrl(apiBase, token) {
  const base = String(apiBase || window.location.origin)
  const url = new URL(base)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = '/api/v1/realtime/ws'
  url.search = token ? `token=${encodeURIComponent(token)}` : ''
  return url.toString()
}

function scheduleReconnect(connectFn) {
  if (reconnectTimer) return
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    connectFn()
  }, 1500)
}

export function subscribeRealtime(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function closeRealtime() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (socket) {
    try {
      socket.close()
    } catch {
      // noop
    }
    socket = null
  }
}

export function startRealtime({ apiBase, tokenProvider }) {
  function connect() {
    if (typeof window === 'undefined' || typeof WebSocket === 'undefined') return
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return

    const token = tokenProvider ? tokenProvider() : null
    const wsUrl = toWsUrl(apiBase, token)
    socket = new WebSocket(wsUrl)

    socket.onopen = () => {
      emit({ topic: 'realtime.connected', payload: {} })
    }

    socket.onmessage = (message) => {
      try {
        const parsed = JSON.parse(String(message.data || '{}'))
        emit(parsed)
      } catch {
        // noop
      }
    }

    socket.onclose = () => {
      emit({ topic: 'realtime.disconnected', payload: {} })
      socket = null
      if (navigator.onLine) scheduleReconnect(connect)
    }

    socket.onerror = () => {
      try {
        socket.close()
      } catch {
        // noop
      }
    }
  }

  connect()

  if (!onlineListenerInstalled && typeof window !== 'undefined') {
    onlineListenerInstalled = true
    window.addEventListener('online', () => {
      if (!socket || socket.readyState === WebSocket.CLOSED) connect()
    })
  }
}
