/**
 * Brother label printer integration via WebUSB.
 * Supports QL-series (QL-560 etc.) and P-touch series (PT-P900Wc etc.).
 *
 * Uses @thermal-label/brother-ql-web for WebUSB communication
 * and @thermal-label/brother-ql-core for raster encoding.
 */

import { requestPrinter } from '@thermal-label/brother-ql-web'
import {
  DEFAULT_MEDIA,
  findMediaByDimensions,
  findMediaByWidth,
} from '@thermal-label/brother-ql-core'

/** Known Brother USB vendor ID */
const BROTHER_VENDOR_ID = 0x04f9

/** Printer connection state */
let connectedPrinter = null
let currentMedia = null
let statusUnsubscribe = null

/**
 * Check if WebUSB is available in this browser.
 * @returns {boolean}
 */
export function isWebUSBSupported() {
  return typeof navigator !== 'undefined' && !!navigator.usb
}

/**
 * Check if a Brother printer is likely connected via WebUSB.
 * @returns {Promise<boolean>}
 */
export async function hasBrotherPrinter() {
  if (!isWebUSBSupported()) return false
  try {
    const devices = await navigator.usb.getDevices()
    return devices.some(d => d.vendorId === BROTHER_VENDOR_ID)
  } catch {
    return false
  }
}

/**
 * Show the browser USB picker and connect to a Brother printer.
 * @returns {Promise<WebBrotherQLPrinter>}
 */
export async function connectPrinter() {
  if (connectedPrinter?.connected) return connectedPrinter

  connectedPrinter = await requestPrinter({
    filters: [{ vendorId: BROTHER_VENDOR_ID }],
  })

  // Debug hook: log the first bytes of every USB write so we can verify the
  // exact command stream the printer receives (e.g. confirm the raster/compression
  // commands carry the `1B 69` ESC prefix). Remove once printing is confirmed working.
  if (connectedPrinter?.transport?.write) {
    const origWrite = connectedPrinter.transport.write.bind(connectedPrinter.transport)
    connectedPrinter.transport.write = (bytes) => {
      const head = Array.from(bytes instanceof Uint8Array ? bytes.slice(0, 48) : bytes).map(
        (b) => (b & 0xff).toString(16).padStart(2, '0'),
      ).join(' ')
      console.log(`[brother-print] → ${bytes.length} bytes | ${head}`)
      return origWrite(bytes)
    }
  }

  try {
    const status = await connectedPrinter.getStatus()
    currentMedia = status.detectedMedia || null
  } catch {
    // Status read may fail on some models — continue without media info
  }

  return connectedPrinter
}

/**
 * Disconnect the current printer.
 */
export async function disconnectPrinter() {
  if (statusUnsubscribe) {
    statusUnsubscribe()
    statusUnsubscribe = null
  }
  if (connectedPrinter) {
    try {
      await connectedPrinter.close()
    } catch {
      // Ignore close errors
    }
    connectedPrinter = null
    currentMedia = null
  }
}

/**
 * Get the currently connected printer instance.
 * @returns {WebBrotherQLPrinter|null}
 */
export function getPrinter() {
  return connectedPrinter
}

/**
 * Get the detected media (label roll/tape) info.
 * @returns {{ widthMm: number, heightMm: number, type: string, name: string }|null}
 */
export function getDetectedMedia() {
  if (!currentMedia) return null
  return {
    widthMm: currentMedia.widthMm || 0,
    heightMm: currentMedia.heightMm ?? currentMedia.length ?? 0,
    type: currentMedia.type || 'unknown',
    name: currentMedia.name || '',
  }
}

/**
 * Re-read the printer status and refresh the detected media info.
 * Useful when the user has loaded a new roll since connecting.
 * @returns {Promise<{ widthMm: number, heightMm: number, type: string, name: string }|null>}
 */
export async function readDetectedMedia() {
  if (!connectedPrinter) return null
  try {
    const status = await connectedPrinter.getStatus()
    currentMedia = status.detectedMedia || null
    return getDetectedMedia()
  } catch {
    return null
  }
}

/**
 * Subscribe to printer status updates.
 * @param {(status: object) => void} callback
 * @returns {() => void} Unsubscribe function
 */
export function onPrinterStatus(callback) {
  if (!connectedPrinter) return () => {}
  if (statusUnsubscribe) {
    statusUnsubscribe()
    statusUnsubscribe = null
  }
  statusUnsubscribe = connectedPrinter.onStatus(callback)
  return statusUnsubscribe
}

/**
 * Get current printer status (paper, ready, errors etc.).
 * @returns {Promise<object>}
 */
export async function getPrinterStatus() {
  if (!connectedPrinter) return null
  try {
    return await connectedPrinter.getStatus()
  } catch {
    return null
  }
}

/**
 * Find the best matching media descriptor for a given width in mm.
  * Common Brother label media presets.
 */
export const LABEL_PRESETS = [
  { id: 'dk-62x100', name: 'DK-22205 (62×100mm)', widthMm: 62, heightMm: 100, family: 'ql' },
  { id: 'dk-62x29', name: 'DK-22201 (62×29mm)', widthMm: 62, heightMm: 29, family: 'ql' },
  { id: 'dk-42x29', name: 'DK-22200 (42×29mm)', widthMm: 42, heightMm: 29, family: 'ql' },
  { id: 'dk-29x90', name: 'DK-12202 (29×90mm)', widthMm: 29, heightMm: 90, family: 'ql' },
  { id: 'dk-continuous-62', name: 'DK-22205 (62mm continuous)', widthMm: 62, heightMm: 0, family: 'ql', continuous: true },
  { id: 'tze-24', name: 'TZe-241 (24mm)', widthMm: 24, heightMm: 0, family: 'pt', continuous: true },
  { id: 'tze-12', name: 'TZe-131 (12mm)', widthMm: 12, heightMm: 0, family: 'pt', continuous: true },
  { id: 'tze-36', name: 'TZe-631 (36mm)', widthMm: 36, heightMm: 0, family: 'pt', continuous: true },
]

/**
 * Render a canvas element to raw image data for the printer.
 *
 * Returns the canvas RGBA pixels as `data` — the underlying renderer
 * (`@mbtech-nl/bitmap`) dithers to 1-bit internally, so we must pass the
 * raw RGBA buffer, not a pre-thresholded array.
 *
 * @param {HTMLCanvasElement} canvas - The label canvas
 * @returns {{ data: Uint8Array, width: number, height: number }}
 */
export function canvasToRawImage(canvas) {
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Could not get canvas 2d context')
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
  return { data: imageData.data, width: canvas.width, height: canvas.height }
}

/**
 * Resolve a valid BrotherQLMedia descriptor for a print job.
 *
 * Prefers an explicitly supplied media, then matches the requested label
 * dimensions against the media registry, then falls back to the media
 * detected from the printer, and finally to the library default (62 mm
 * continuous). This guarantees the printer always receives a well-formed
 * media descriptor — passing `undefined` here makes the encoder throw.
 *
 * @param {object} [options]
 * @param {object} [options.media] - Explicit BrotherQLMedia descriptor
 * @param {number} [options.widthMm] - Label width in mm
 * @param {number} [options.heightMm] - Label height in mm (0 = continuous)
 * @returns {object} BrotherQLMedia descriptor
 */
export function resolvePrintMedia(options = {}) {
  let media
  if (options.media) media = options.media
  else if (options.widthMm) {
    if (options.heightMm) {
      media = findMediaByDimensions(options.widthMm, options.heightMm)
    } else {
      const candidates = findMediaByWidth(options.widthMm)
      media = candidates.find((m) => m.type === 'continuous') || candidates[0]
    }
  }
  if (!media) media = currentMedia || DEFAULT_MEDIA

  // The Brother raster protocol requires every raster line to span the full
  // print head (`headDots`). Some die-cut descriptors (e.g. DK-11218) report
  // margins that do not sum to the head width, so the encoder emits rows
  // narrower than the head and the printer rejects them (a "System error" /
  // transmission error). Re-align the printable window within the head,
  // centred, so the transmitted row width always matches the physical head
  // (e.g. 413 printable dots centred in a 720-dot QL-560 head).
  const engine = connectedPrinter?.device?.engines?.[0]
  const headDots = engine?.headDots || engine?.config?.headDots
  if (media && headDots && media.type === 'die-cut') {
    const total = (media.leftMarginPins || 0) + media.printableDots + (media.rightMarginPins || 0)
    if (total !== headDots && media.printableDots <= headDots) {
      const leftMargin = Math.floor((headDots - media.printableDots) / 2)
      const rightMargin = headDots - media.printableDots - leftMargin
      media = {
        ...media,
        leftMarginPins: leftMargin,
        rightMarginPins: rightMargin,
      }
    }
  }
  return media
}

/**
 * Print a canvas on the connected Brother printer.
 *
 * @param {HTMLCanvasElement} canvas - The label canvas to print
 * @param {object} options
 * @param {boolean} options.cut - Cut after each label (default: true)
 * @param {number} options.copies - Number of copies (default: 1)
 * @param {number} [options.widthMm] - Label width in mm (for media match)
 * @param {number} [options.heightMm] - Label height in mm (0 = continuous)
 * @param {object} [options.media] - Explicit media descriptor
 * @returns {Promise<void>}
 */
export async function printCanvas(canvas, options = {}) {
  if (!connectedPrinter) throw new Error('No printer connected')
  if (!connectedPrinter.connected) throw new Error('Printer is not connected')

  const { cut = true, copies = 1, widthMm, heightMm, media } = options
  const rawImage = canvasToRawImage(canvas)
  const resolvedMedia = resolvePrintMedia({ media, widthMm, heightMm })

  for (let i = 0; i < copies; i++) {
    await connectedPrinter.print(rawImage, resolvedMedia, {
      autoCut: cut,
      cutAtEnd: cut,
      compress: connectedPrinter?.device?.engines?.[0]?.capabilities?.compression === true,
    })
  }
}

/**
 * Print multiple canvases (one per label) on the connected printer.
 *
 * @param {HTMLCanvasElement[]} canvases - Array of label canvases
 * @param {object} options
 * @param {boolean} options.cut - Cut between labels (default: true)
 * @param {number} [options.widthMm] - Label width in mm (for media match)
 * @param {number} [options.heightMm] - Label height in mm (0 = continuous)
 * @param {object} [options.media] - Explicit media descriptor
 * @returns {Promise<void>}
 */
export async function printMultipleLabels(canvases, options = {}) {
  if (!connectedPrinter) throw new Error('No printer connected')
  if (!connectedPrinter.connected) throw new Error('Printer is not connected')

  const { cut = true, widthMm, heightMm, media, rotate } = options
  const resolvedMedia = resolvePrintMedia({ media, widthMm, heightMm })

  for (let i = 0; i < canvases.length; i++) {
    const rawImage = canvasToRawImage(canvases[i])
    await connectedPrinter.print(rawImage, resolvedMedia, {
      autoCut: cut,
      cutAtEnd: cut,
      rotate,
      compress: connectedPrinter?.device?.engines?.[0]?.capabilities?.compression === true,
    })
  }
}
