/**
 * Brother label printer integration via WebUSB.
 * Supports QL-series (QL-560 etc.) and P-touch series (PT-P900Wc etc.).
 *
 * Uses @thermal-label/brother-ql-web for WebUSB communication
 * and @thermal-label/brother-ql-core for raster encoding.
 */

import { requestPrinter, WebBrotherQLPrinter } from '@thermal-label/brother-ql-web'
import { findMedia, MEDIA } from '@thermal-label/brother-ql-core'

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

  try {
    const status = await connectedPrinter.getStatus()
    currentMedia = status.media
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
 * @returns {{ width: number, type: string }|null}
 */
export function getDetectedMedia() {
  if (!currentMedia) return null
  return {
    width: currentMedia.width || 0,
    type: currentMedia.type || 'unknown',
    name: currentMedia.name || '',
    length: currentMedia.length || 0,
  }
}

/**
 * Subscribe to printer status updates.
 * @param {(status: object) => void} callback
 * @returns {() => void} Unsubscribe function
 */
export function onPrinterStatus(callback) {
  if (!connectedPrinter) return () => {}
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
 * @param {number} widthMm - Label width in millimeters
 * @returns {object|null}
 */
export function findMediaByWidth(widthMm) {
  return findMedia(widthMm) || null
}

/**
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
 * Converts to 1-bit black and white (dithered).
 *
 * @param {HTMLCanvasElement} canvas - The label canvas
 * @returns {RawImageData}
 */
export function canvasToRawImage(canvas) {
  const ctx = canvas.getContext('2d')
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
  const { data, width, height } = imageData

  // Convert to grayscale then threshold to 1-bit
  const pixels = new Uint8Array(width * height)
  for (let i = 0; i < width * height; i++) {
    const r = data[i * 4]
    const g = data[i * 4 + 1]
    const b = data[i * 4 + 2]
    const gray = 0.299 * r + 0.587 * g + 0.114 * b
    pixels[i] = gray < 128 ? 0 : 255
  }

  return { pixels, width, height }
}

/**
 * Print a canvas on the connected Brother printer.
 *
 * @param {HTMLCanvasElement} canvas - The label canvas to print
 * @param {object} options
 * @param {boolean} options.cut - Cut after each label (default: true)
 * @param {number} options.copies - Number of copies (default: 1)
 * @returns {Promise<void>}
 */
export async function printCanvas(canvas, options = {}) {
  if (!connectedPrinter) throw new Error('No printer connected')
  if (!connectedPrinter.connected) throw new Error('Printer is not connected')

  const { cut = true, copies = 1 } = options
  const rawImage = canvasToRawImage(canvas)

  for (let i = 0; i < copies; i++) {
    await connectedPrinter.print(rawImage, currentMedia, {
      cut,
    })
  }
}

/**
 * Print multiple canvases (one per label) on the connected printer.
 *
 * @param {HTMLCanvasElement[]} canvases - Array of label canvases
 * @param {object} options
 * @param {boolean} options.cut - Cut between labels (default: true)
 * @returns {Promise<void>}
 */
export async function printMultipleLabels(canvases, options = {}) {
  if (!connectedPrinter) throw new Error('No printer connected')
  if (!connectedPrinter.connected) throw new Error('Printer is not connected')

  const { cut = true } = options

  for (let i = 0; i < canvases.length; i++) {
    const rawImage = canvasToRawImage(canvases[i])
    await connectedPrinter.print(rawImage, currentMedia, {
      cut: cut && i < canvases.length - 1,
    })
  }
}
