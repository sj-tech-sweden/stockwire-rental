import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../boot/axios'

export const useReportsStore = defineStore('reports', () => {
  const letterheads = ref([])
  const templates = ref([])
  const reportLogs = ref([])
  const loadingLetterheads = ref(false)
  const loadingTemplates = ref(false)

  // ── Letterheads ────────────────────────────────────────────────────────────

  async function fetchLetterheads() {
    loadingLetterheads.value = true
    try {
      const { data } = await api.get('/api/v1/reports/letterheads')
      letterheads.value = data
      return data
    } catch (error) {
      console.error('Failed to fetch letterheads:', error)
      throw error
    } finally {
      loadingLetterheads.value = false
    }
  }

  async function createLetterhead(payload) {
    const { data } = await api.post('/api/v1/reports/letterheads', payload)
    letterheads.value = [data, ...letterheads.value.filter(l => l.id !== data.id)]
    return data
  }

  async function uploadLetterhead(file, meta = {}) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('name', meta.name || file.name)
    if (meta.is_default) formData.append('is_default', 'true')
    if (meta.margin_top_mm != null) formData.append('margin_top_mm', String(meta.margin_top_mm))
    if (meta.margin_bottom_mm != null) formData.append('margin_bottom_mm', String(meta.margin_bottom_mm))
    if (meta.margin_left_mm != null) formData.append('margin_left_mm', String(meta.margin_left_mm))
    if (meta.margin_right_mm != null) formData.append('margin_right_mm', String(meta.margin_right_mm))

    const { data } = await api.post('/api/v1/reports/letterheads/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    letterheads.value = [data, ...letterheads.value.filter(l => l.id !== data.id)]
    return data
  }

  async function updateLetterhead(id, payload) {
    const { data } = await api.put(`/api/v1/reports/letterheads/${id}`, payload)
    const idx = letterheads.value.findIndex(l => l.id === id)
    if (idx >= 0) letterheads.value[idx] = data
    return data
  }

  async function deleteLetterhead(id) {
    await api.delete(`/api/v1/reports/letterheads/${id}`)
    letterheads.value = letterheads.value.filter(l => l.id !== id)
  }

  // ── Templates ──────────────────────────────────────────────────────────────

  async function fetchTemplates(params = {}) {
    loadingTemplates.value = true
    try {
      const { data } = await api.get('/api/v1/reports/templates', { params })
      templates.value = data
      return data
    } catch (error) {
      console.error('Failed to fetch templates:', error)
      throw error
    } finally {
      loadingTemplates.value = false
    }
  }

  async function getTemplate(id) {
    const { data } = await api.get(`/api/v1/reports/templates/${id}`)
    return data
  }

  async function createTemplate(payload) {
    const { data } = await api.post('/api/v1/reports/templates', payload)
    templates.value = [data, ...templates.value.filter(t => t.id !== data.id)]
    return data
  }

  async function updateTemplate(id, payload) {
    const { data } = await api.put(`/api/v1/reports/templates/${id}`, payload)
    const idx = templates.value.findIndex(t => t.id === id)
    if (idx >= 0) templates.value[idx] = data
    return data
  }

  async function deleteTemplate(id) {
    await api.delete(`/api/v1/reports/templates/${id}`)
    templates.value = templates.value.filter(t => t.id !== id)
  }

  async function duplicateTemplate(id) {
    const { data } = await api.post(`/api/v1/reports/templates/${id}/duplicate`)
    templates.value = [data, ...templates.value]
    return data
  }

  async function previewTemplate(templateId, entityType = 'job', entityId = 1, language = 'en') {
    const { data } = await api.get(`/api/v1/reports/templates/${templateId}/preview`, {
      params: { entity_type: entityType, entity_id: entityId, language },
    })
    return data
  }

  // ── Generation ─────────────────────────────────────────────────────────────

  async function generateReport(payload) {
    const { data } = await api.post('/api/v1/reports/generate', payload)
    return data
  }

  async function previewReport(payload, responseType = 'blob') {
    const response = await api.post('/api/v1/reports/preview', payload, {
      responseType,
    })
    return response.data
  }

  async function fetchReportLogs(params = {}) {
    const { data } = await api.get('/api/v1/reports/logs', { params })
    reportLogs.value = data
    return data
  }

  // ── Data Source Schema ─────────────────────────────────────────────────────

  async function fetchDataSourceSchema(sourceType) {
    const { data } = await api.get(`/api/v1/reports/data-source/${sourceType}/schema`)
    return data
  }

  return {
    letterheads,
    templates,
    reportLogs,
    loadingLetterheads,
    loadingTemplates,
    fetchLetterheads,
    createLetterhead,
    uploadLetterhead,
    updateLetterhead,
    deleteLetterhead,
    fetchTemplates,
    getTemplate,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    duplicateTemplate,
    previewTemplate,
    generateReport,
    previewReport,
    fetchReportLogs,
    fetchDataSourceSchema,
  }
})
