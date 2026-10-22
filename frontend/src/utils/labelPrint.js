// Shared label rendering + printing pipeline.
//
// Used by both the label editor (LabelsPage) and the inventory "Print labels"
// dialog so labels can be printed directly from either place — via a connected
// Brother printer (WebUSB, direct) or a normal system printer (browser print).
import JsBarcode from 'jsbarcode'
import QRCode from 'qrcode'
import { useSettingsStore } from '../stores/settings'
import { useInventoryStore } from '../stores/inventory'
import { getApiBaseUrl } from './runtime-config'
import {
  getDetectedMedia,
  getPrinter,
  getPrinterStatus,
  printMultipleLabels,
  resolvePrintMedia,
} from './brother-print'

const settings = useSettingsStore()
const inventoryStore = useInventoryStore()
const apiBaseUrl = getApiBaseUrl()

// Built-in and runtime-registered size presets. Keys are `WxH` (mm) or `a4-3x8`.
// The `WxH` entries are added at runtime when a size is detected from the
// printer, so this object is mutated by callers.
export const PRINT_PRESETS = {
  '62x29': { key: '62x29', mode: 'single', labelW: 62, labelH: 29 },
  '62x100': { key: '62x100', mode: 'single', labelW: 62, labelH: 100 },
  '50x25': { key: '50x25', mode: 'single', labelW: 50, labelH: 25 },
  'a4-3x8': {
    key: 'a4-3x8',
    label: 'A4 grid 3 x 8',
    mode: 'grid',
    pageW: 210,
    pageH: 297,
    cols: 3,
    rows: 8,
    labelW: 63.5,
    labelH: 33.9,
    gapX: 2.5,
    gapY: 0,
    marginX: 8,
    marginY: 12,
  },
}

export function getPreset(key) {
  const known = PRINT_PRESETS[key]
  if (known) return known
  // A `WxH` key (e.g. a size detected from the printer and saved with a
  // template) resolves directly so the design still sizes correctly even when
  // the runtime preset is no longer registered.
  const match = String(key || '').match(/^(\d+)x(\d+)$/)
  if (match) {
    return { key, mode: 'single', labelW: Number(match[1]), labelH: Number(match[2]) }
  }
  return PRINT_PRESETS['62x29']
}

export function orientedDims(labelW, labelH, wideLabel) {
  return wideLabel
    ? { w: Number(labelH || 0), h: Number(labelW || 0) }
    : { w: Number(labelW || 0), h: Number(labelH || 0) }
}

export function normalizeElement(partial) {
  return {
    id: partial.id || `el-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    kind: partial.kind || 'field',
    source: partial.source || '',
    text: partial.text || '',
    x: Number(partial.x || 10),
    y: Number(partial.y || 10),
    w: Number(partial.w || 140),
    h: Number(partial.h || 30),
    fontSize: Number(partial.fontSize || 12),
  }
}

// Build the row objects for each entity type, enriching device/case rows with
// their parent product and current zone (flat fields + nested objects reachable
// via dot-path sources like `product.sku` / `zone.name`).
export function buildRowsByEntityType() {
  const productById = new Map((inventoryStore.products || []).map(item => [item.id, item]))
  const zoneById = new Map((inventoryStore.zones || []).map(item => [item.id, item]))

  const zonePath = (zone) => {
    if (!zone) return ''
    const parts = []
    const seen = new Set()
    let cur = zone
    while (cur && !seen.has(cur.id)) {
      seen.add(cur.id)
      parts.unshift(cur.name || '')
      cur = cur.parent_id != null ? zoneById.get(cur.parent_id) || null : null
    }
    return parts.filter(Boolean).join(' / ')
  }

  const enrichDevice = (device) => {
    const product = productById.get(device.product_id) || null
    const zone = device.location_zone_id != null ? (zoneById.get(device.location_zone_id) || null) : null
    return {
      ...device,
      product,
      zone,
      product_name: product?.name ?? '',
      product_sku: product?.sku ?? '',
      product_category: product?.category ?? '',
      product_brand: product?.brand ?? '',
      product_description: product?.description ?? '',
      location_name: zone?.name ?? '',
      zone_tree: zonePath(zone),
    }
  }

  const devices = inventoryStore.devices || []
  return {
    device: devices.map(enrichDevice),
    product: inventoryStore.products || [],
    location: inventoryStore.zones || [],
    case: devices
      .filter((device) => {
        const product = productById.get(device.product_id)
        return product?.product_type === 'case'
      })
      .map(enrichDevice),
  }
}

export function getNestedValue(obj, path) {
  if (obj == null) return ''
  let cur = obj
  for (const part of String(path).split('.')) {
    if (cur == null) return ''
    cur = cur[part]
  }
  return cur == null ? '' : cur
}

// Resolve a (possibly dotted) source path against a row, e.g. `product.sku`.
// Also handles `business.*` (company profile) and `custom_fields.*`.
export function resolveValue(row, source) {
  const key = String(source || '').trim()
  if (!key) return ''
  if (key.startsWith('business.')) {
    const businessKey = key.slice('business.'.length)
    return settings.companyProfile?.[businessKey] ?? ''
  }
  if (key.startsWith('custom_fields.')) {
    const customKey = key.slice('custom_fields.'.length)
    return row?.custom_fields?.[customKey] ?? ''
  }
  return getNestedValue(row, key) ?? ''
}

export function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export function barcodeSvg(value, widthPx, heightPx) {
  const content = String(value ?? '').trim()
  if (!content) return ''
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  try {
    JsBarcode(svg, content, {
      format: 'CODE128',
      displayValue: false,
      margin: 0,
      width: 1.2,
      height: Math.max(16, Number(heightPx || 44) - 2),
    })
    svg.setAttribute('width', String(Math.max(40, Number(widthPx || 120))))
    svg.setAttribute('height', String(Math.max(20, Number(heightPx || 44))))
    return svg.outerHTML
  } catch {
    return ''
  }
}

export async function qrDataUrl(value, sizePx) {
  const content = String(value ?? '').trim()
  if (!content) return ''
  try {
    return await QRCode.toDataURL(content, { margin: 0, width: Math.max(32, Number(sizePx || 96)) })
  } catch {
    return ''
  }
}

export function resolveLogoUrl() {
  const profile = settings.companyProfile || {}
  const darkWideId = Number(profile.logo_dark_wide_file_id || 0)
  const darkSmallId = Number(profile.logo_dark_small_file_id || 0)
  const defaultId = Number(profile.logo_file_id || 0)
  const lightWideId = Number(profile.logo_light_wide_file_id || 0)
  const lightSmallId = Number(profile.logo_light_small_file_id || 0)

  const publicRaw = [
    darkWideId > 0 ? `/api/v1/storage/public/company-logo/dark-wide?v=${darkWideId}` : '',
    darkSmallId > 0 ? `/api/v1/storage/public/company-logo/dark-small?v=${darkSmallId}` : '',
    defaultId > 0 ? `/api/v1/storage/public/company-logo?v=${defaultId}` : '',
    lightWideId > 0 ? `/api/v1/storage/public/company-logo/light-wide?v=${lightWideId}` : '',
    lightSmallId > 0 ? `/api/v1/storage/public/company-logo/light-small?v=${lightSmallId}` : '',
  ].find(Boolean)

  const raw = publicRaw || [
    profile.logo_dark_wide_url,
    profile.logo_dark_small_url,
    profile.logo_url,
    profile.logo_light_wide_url,
    profile.logo_light_small_url,
  ].map(value => String(value || '').trim()).find(Boolean) || ''
  if (!raw) return ''
  if (/^(https?:|data:|blob:)/i.test(raw)) return raw
  if (raw.startsWith('/')) return `${apiBaseUrl}${raw}`
  return `${apiBaseUrl}/${raw}`
}

export function resolveLogoUrlBySource(source) {
  const key = String(source || '').trim()
  const profile = settings.companyProfile || {}
  if (!key) return resolveLogoUrl()

  const bySource = {
    'business.logo_url': {
      id: Number(profile.logo_file_id || 0),
      publicPath: '/api/v1/storage/public/company-logo',
      fallbackUrl: profile.logo_url,
    },
    'business.logo_light_wide_url': {
      id: Number(profile.logo_light_wide_file_id || 0),
      publicPath: '/api/v1/storage/public/company-logo/light-wide',
      fallbackUrl: profile.logo_light_wide_url,
    },
    'business.logo_light_small_url': {
      id: Number(profile.logo_light_small_file_id || 0),
      publicPath: '/api/v1/storage/public/company-logo/light-small',
      fallbackUrl: profile.logo_light_small_url,
    },
    'business.logo_dark_wide_url': {
      id: Number(profile.logo_dark_wide_file_id || 0),
      publicPath: '/api/v1/storage/public/company-logo/dark-wide',
      fallbackUrl: profile.logo_dark_wide_url,
    },
    'business.logo_dark_small_url': {
      id: Number(profile.logo_dark_small_file_id || 0),
      publicPath: '/api/v1/storage/public/company-logo/dark-small',
      fallbackUrl: profile.logo_dark_small_url,
    },
  }

  const selected = bySource[key]
  if (!selected) return resolveLogoUrl()
  if (selected.id > 0) return `${apiBaseUrl}${selected.publicPath}?v=${selected.id}`

  const fallback = String(selected.fallbackUrl || '').trim()
  if (!fallback) return ''
  if (/^(https?:|data:|blob:)/i.test(fallback)) return fallback
  if (fallback.startsWith('/')) return `${apiBaseUrl}${fallback}`
  return `${apiBaseUrl}/${fallback}`
}

export function resolveLogoUrlForElement(item) {
  if (item?.kind !== 'logo') return ''
  return resolveLogoUrlBySource(item?.source)
}

export function elementToMm(item, labelWmm, labelHmm, canvasWpx, canvasHpx) {
  const baseW = Math.max(1, Number(canvasWpx || 1))
  const baseH = Math.max(1, Number(canvasHpx || 1))
  return {
    x: (Number(item.x || 0) / baseW) * labelWmm,
    y: (Number(item.y || 0) / baseH) * labelHmm,
    w: Math.max(1, (Number(item.w || 1) / baseW) * labelWmm),
    h: Math.max(1, (Number(item.h || 1) / baseH) * labelHmm),
    fontMm: Math.max(1.8, (Number(item.fontSize || 12) / baseW) * labelWmm),
  }
}

export async function renderElementHtml(item, row, labelWmm, labelHmm, canvasWpx, canvasHpx) {
  const mm = elementToMm(item, labelWmm, labelHmm, canvasWpx, canvasHpx)
  if (item.kind === 'logo') {
    const logo = resolveLogoUrlForElement(item)
    if (!logo) return `<div style="position:absolute;left:${mm.x}mm;top:${mm.y}mm;width:${mm.w}mm;height:${mm.h}mm;font-size:${mm.fontMm}mm;">LOGO</div>`
    return `<img src="${escapeHtml(logo)}" style="position:absolute;left:${mm.x}mm;top:${mm.y}mm;width:${mm.w}mm;height:${mm.h}mm;object-fit:contain;" crossorigin="anonymous" />`
  }
  if (item.kind === 'text') {
    return `<div style="position:absolute;left:${mm.x}mm;top:${mm.y}mm;width:${mm.w}mm;height:${mm.h}mm;font-size:${mm.fontMm}mm;overflow:hidden;color:#111;">${escapeHtml(item.text || '')}</div>`
  }

  const value = resolveValue(row, item.source)
  if (item.kind === 'barcode') {
    const svg = barcodeSvg(value, Math.round(mm.w * 3.78), Math.round(mm.h * 3.78))
    return `<div style="position:absolute;left:${mm.x}mm;top:${mm.y}mm;width:${mm.w}mm;height:${mm.h}mm;overflow:hidden;">${svg}</div>`
  }
  if (item.kind === 'qrcode') {
    const sizePx = Math.round(Math.min(mm.w, mm.h) * 3.78)
    const url = await qrDataUrl(value, sizePx)
    return `<div style="position:absolute;left:${mm.x}mm;top:${mm.y}mm;width:${mm.w}mm;height:${mm.h}mm;display:flex;align-items:center;justify-content:center;">${url ? `<img src="${url}" style="max-width:100%;max-height:100%;" />` : ''}</div>`
  }
  return `<div style="position:absolute;left:${mm.x}mm;top:${mm.y}mm;width:${mm.w}mm;height:${mm.h}mm;font-size:${mm.fontMm}mm;overflow:hidden;color:#111;">${escapeHtml(value)}</div>`
}

export async function renderLabelInnerHtml(row, elements, labelWmm, labelHmm, canvasWpx, canvasHpx) {
  const blocks = []
  for (const item of elements) {
    blocks.push(await renderElementHtml(item, row, labelWmm, labelHmm, canvasWpx, canvasHpx))
  }
  return `<div style="position:relative;width:${labelWmm}mm;height:${labelHmm}mm;overflow:hidden;">${blocks.join('')}</div>`
}

// Render a single label (the `elements` design) for `row` into a 2D canvas at
// the print resolution. `canvasWpx`/`canvasHpx` are the editor canvas pixel
// dimensions the element coordinates are stored in.
export async function renderLabelToCanvas(ctx, row, elements, canvasW, canvasH, labelWmm, labelHmm, canvasWpx, canvasHpx) {
  const scaleX = canvasW / Math.max(1, canvasWpx)
  const scaleY = canvasH / Math.max(1, canvasHpx)

  for (const el of elements) {
    const x = el.x * scaleX
    const y = el.y * scaleY
    const w = (el.w || 40) * scaleX
    const h = (el.h || 10) * scaleY
    const fontSize = (el.fontSize || 12) * scaleX

    if (el.kind === 'text' || el.kind === 'field') {
      const text = el.kind === 'text' ? el.text : (resolveValue(row, el.source) || '')
      ctx.fillStyle = '#000'
      ctx.font = `${Math.round(fontSize)}px Arial`
      ctx.textBaseline = 'top'
      ctx.fillText(text, x, y, w)
    } else if (el.kind === 'barcode') {
      const value = resolveValue(row, el.source) || row.asset_tag || row.sku || row.code || ''
      if (value) {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
        JsBarcode(svg, value, { format: 'CODE128', width: 1, height: h, displayValue: false })
        const img = new Image()
        const svgBlob = new Blob([svg.outerHTML], { type: 'image/svg+xml' })
        const url = URL.createObjectURL(svgBlob)
        await new Promise((resolve, reject) => {
          img.onload = resolve
          img.onerror = () => {
            URL.revokeObjectURL(url)
            reject(new Error('Failed to load barcode SVG'))
          }
          img.src = url
        })
        ctx.drawImage(img, x, y, w, h)
        URL.revokeObjectURL(url)
      }
    } else if (el.kind === 'qrcode') {
      const value = resolveValue(row, el.source) || row.asset_tag || row.sku || ''
      if (value) {
        const dataUrl = await QRCode.toDataURL(value, { width: Math.round(w), margin: 0 })
        const img = new Image()
        await new Promise((resolve, reject) => {
          img.onload = resolve
          img.onerror = () => reject(new Error('Failed to load QR code image'))
          img.src = dataUrl
        })
        ctx.drawImage(img, x, y, w, h)
      }
    } else if (el.kind === 'logo') {
      const logoUrl = resolveLogoUrlBySource(el.source)
      if (logoUrl) {
        const img = new Image()
        img.crossOrigin = 'anonymous'
        await new Promise((resolve) => {
          img.onload = resolve
          img.onerror = resolve
          img.src = logoUrl
        })
        if (img.naturalWidth > 0) {
          ctx.drawImage(img, x, y, w, h)
        }
      }
    }
  }
}

// Diagnostic pattern drawn in the template (pre-rotation) frame; kept available
// for the calibration print.
export function drawCalibrationPattern(ctx, w, h) {
  const fontPx = Math.round(h * 0.13)
  const block = Math.round(h * 0.16)
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, w, h)
  ctx.strokeStyle = '#000'
  ctx.lineWidth = Math.max(4, Math.round(h * 0.02))
  ctx.strokeRect(ctx.lineWidth / 2, ctx.lineWidth / 2, w - ctx.lineWidth, h - ctx.lineWidth)
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, block, block)
  ctx.font = `bold ${fontPx}px Arial`
  ctx.textBaseline = 'top'
  ctx.textAlign = 'left'
  ctx.fillText('TOP', block + 12, 8)
  ctx.textAlign = 'right'
  ctx.fillText('BOTTOM', w - 12, h - fontPx - 8)
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillText('LEFT', 12, h / 2)
  ctx.textAlign = 'right'
  ctx.fillText('RIGHT', w - 12, h / 2)
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
}

function chunk(items, size) {
  const result = []
  for (let idx = 0; idx < items.length; idx += size) {
    result.push(items.slice(idx, idx + size))
  }
  return result
}

// Print rows to a normal system printer via a browser print window.
export async function printRowsBrowser({ rows, elements, printPreset, profileKey, canvasWpx, canvasHpx, labelWmm, labelHmm, brotherHint, notify }) {
  const preset = getPreset(printPreset)
  const pxPerMm = 300 / 25.4
  // Prefer the design canvas orientation so the printed sheet matches how the
  // template was laid out; fall back to the passed/fixed preset dimensions.
  let pageW = Number(labelWmm ?? preset.labelW)
  let pageH = Number(labelHmm ?? preset.labelH)
  if (canvasWpx && canvasHpx) {
    pageW = canvasWpx / pxPerMm
    pageH = canvasHpx / pxPerMm
  }
  const popup = window.open('', '_blank', 'width=1200,height=900')
  if (!popup) {
    notify?.({ type: 'warning', timeout: 5000, message: 'Popup blocked. Allow popups for this site to open the print dialog automatically.' })
    return
  }

  if (profileKey === 'brother_ql560' && brotherHint) {
    notify?.({ type: 'info', timeout: 7000, message: brotherHint })
  }

  let body = ''
  if (preset.mode === 'single') {
    for (const row of rows) {
      const inner = await renderLabelInnerHtml(row, elements, pageW, pageH, canvasWpx, canvasHpx)
      body += `<div class="sheet single">${inner}</div>`
    }
  } else {
    const perSheet = Number(preset.cols || 1) * Number(preset.rows || 1)
    const pages = chunk(rows, perSheet)
    for (const pageRows of pages) {
      let cells = ''
      for (let i = 0; i < perSheet; i += 1) {
        const row = pageRows[i]
        if (!row) {
          cells += '<div class="cell empty"></div>'
          continue
        }
        const inner = await renderLabelInnerHtml(row, elements, preset.labelW, preset.labelH, canvasWpx, canvasHpx)
        cells += `<div class="cell">${inner}</div>`
      }
      body += `<div class="sheet grid">${cells}</div>`
    }
  }

  const pageRule = preset.mode === 'single'
    ? `@page { size: ${pageW}mm ${pageH}mm; margin: 0; }`
    : '@page { size: A4; margin: 0; }'

  const gridRule = preset.mode === 'grid'
    ? `.sheet.grid { width: ${preset.pageW}mm; min-height: ${preset.pageH}mm; display:grid; grid-template-columns: repeat(${preset.cols}, ${preset.labelW}mm); grid-template-rows: repeat(${preset.rows}, ${preset.labelH}mm); column-gap:${preset.gapX}mm; row-gap:${preset.gapY}mm; padding:${preset.marginY}mm ${preset.marginX}mm; box-sizing:border-box; page-break-after: always; } .cell { width:${preset.labelW}mm; height:${preset.labelH}mm; overflow:hidden; }`
    : '.sheet.single { page-break-after: always; }'

  popup.document.write(`<!doctype html><html><head><title>Print Labels</title><style>
    ${pageRule}
    body { margin: 0; background: #fff; font-family: Arial, sans-serif; color: #111; }
    ${gridRule}
    @media print {
      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .sheet.single { break-after: page; }
      .sheet.single:last-child { break-after: auto; }
    }
    @media screen { .sheet { border: 1px dashed #cbd5e1; margin: 6mm auto; } }
  </style></head><body>${body}</body></html>`)
  popup.document.close()

  // Give images a moment to load before invoking the print dialog.
  const images = Array.from(popup.document.images || [])
  const pending = images.filter(img => !img.complete)
  if (pending.length) {
    await Promise.race([
      Promise.all(pending.map(img => new Promise(resolve => {
        img.addEventListener('load', resolve, { once: true })
        img.addEventListener('error', resolve, { once: true })
      }))),
      new Promise(resolve => setTimeout(resolve, 3000)),
    ])
  }
  popup.focus()
  popup.print()
}

// Print rows directly to a connected Brother printer (WebUSB).
export async function printRowsDirect({ rows, elements, canvasWpx, canvasHpx, cutLabels, calibration = false, notify }) {
  const printer = getPrinter()
  if (!printer?.connected) {
    notify?.({ type: 'warning', message: 'No printer connected' })
    return
  }

  const pxPerMm = 300 / 25.4
  // The design canvas is the single source of truth for orientation. Derive the
  // label's millimetre dimensions from the saved canvas so the print orientation
  // follows how the template was actually laid out — a portrait "62x100" or a
  // wide-swapped "62x29" — instead of a preset+flag derivation that inverts for
  // portrait presets and stretches/squashes the output.
  const labelW = (canvasWpx || 1) / pxPerMm
  const labelH = (canvasHpx || 1) / pxPerMm
  const detected = getDetectedMedia()

  // Size the bitmap to the printer's exact media dot area so the encoder does
  // not reject it (die-cut media prints a fixed number of rows).
  const resolved = resolvePrintMedia({
    widthMm: detected?.widthMm || labelW,
    heightMm: detected?.heightMm || labelH,
  })
  const dotW = resolved.printableDots
  const dotH = resolved.type === 'die-cut'
    ? resolved.dieCutMaskedAreaDots
    : Math.max(1, Math.round((detected?.heightMm || labelH) * pxPerMm))

  const mediaWide = (resolved.widthMm || 0) > (resolved.heightMm || 0)
  const labelWide = labelW > labelH
  const rotate = mediaWide !== labelWide ? 90 : 0

  // Temp canvas: the template at its own orientation, sized to the printer's
  // exact media dot area (transposed for the rotation).
  const tempW = rotate === 90 ? dotH : dotW
  const tempH = rotate === 90 ? dotW : dotH

  const canvases = []
  for (const row of (calibration ? [null] : rows)) {
    const temp = document.createElement('canvas')
    temp.width = tempW
    temp.height = tempH
    const tctx = temp.getContext('2d')
    if (!tctx) throw new Error('Could not get 2d context for temp canvas')
    tctx.fillStyle = '#fff'
    tctx.fillRect(0, 0, tempW, tempH)
    if (calibration) drawCalibrationPattern(tctx, tempW, tempH)
    else await renderLabelToCanvas(tctx, row, elements, tempW, tempH, labelW, labelH, canvasWpx, canvasHpx)
    canvases.push(temp)
  }

  await printMultipleLabels(canvases, {
    cut: cutLabels,
    widthMm: resolved.widthMm || labelW,
    heightMm: resolved.heightMm || labelH,
    rotate,
  })

  notify?.({ type: 'positive', message: `Printed ${canvases.length} label(s)` })

  // Surface printer-reported errors (e.g. media end) explicitly.
  try {
    const postStatus = await getPrinterStatus()
    const postErrs = postStatus?.errors || []
    if (postErrs.length) {
      notify?.({
        type: 'warning',
        message: `Printer errors: ${postErrs.map((e) => e.message).join(', ')}`,
        timeout: 8000,
      })
    }
  } catch {
    // Ignore failures reading status after a successful print.
  }
}
