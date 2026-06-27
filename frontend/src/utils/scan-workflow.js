export function workflowRequirementProgress(row) {
  const required = Number(row?.quantity_required || 0)
  const picked = Number(row?.quantity_picked || 0)
  if (required <= 0) {
    return {
      required,
      picked,
      packed: Math.max(picked, 0),
      percent: picked > 0 ? 100 : 0,
    }
  }

  const packed = Math.min(Math.max(picked, 0), required)
  return {
    required,
    picked,
    packed,
    percent: Math.min(Math.round((packed / required) * 100), 100),
  }
}

export function resolveDeviceScanCode(device) {
  return [device?.asset_tag, device?.barcode, device?.qr_code, device?.rfid, device?.serial_number]
    .map(value => String(value || '').trim())
    .find(Boolean) || ''
}

export function buildScanJobLink(action, job) {
  if (!job?.id) return { path: '/scan' }
  return {
    path: '/scan',
    query: {
      action,
      jobId: String(job.id),
      jobCode: String(job.job_code || ''),
    },
  }
}

export function isWorkflowRequirementComplete(row) {
  return Number(row?.remaining || 0) <= 0
}

export function splitWorkflowRequirements(rows = []) {
  const pending = []
  const completed = []
  for (const row of rows) {
    if (isWorkflowRequirementComplete(row)) completed.push(row)
    else pending.push(row)
  }
  return { pending, completed }
}

export function summarizeWorkflowRequirements(rows = []) {
  const totalRequired = rows.reduce((sum, row) => sum + Number(row?.quantity_required || 0), 0)
  const totalPacked = rows.reduce((sum, row) => sum + workflowRequirementProgress(row).packed, 0)
  const completedCount = rows.filter(isWorkflowRequirementComplete).length
  return {
    totalRequired,
    totalPacked,
    completedCount,
    totalCount: rows.length,
    percent: totalRequired > 0 ? Math.min(Math.round((totalPacked / totalRequired) * 100), 100) : 0,
  }
}
