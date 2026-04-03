import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// --- Dashboard ---
export const getDashboardSummary = () => api.get('/dashboard/summary')
export const getDailySummary = (date?: string) =>
  api.get('/dashboard/daily-summary', { params: { date } })
export const getReports = (limit = 30) =>
  api.get('/dashboard/reports', { params: { limit } })

// --- Requests ---
export const getRequestSummary = (hours = 24, service?: string) =>
  api.get('/requests/summary', { params: { hours, service } })
export const getRequestsByService = (hours = 24) =>
  api.get('/requests/by-service', { params: { hours } })
export const getTopEndpoints = (hours = 24, sortBy = 'count', limit = 20, service?: string) =>
  api.get('/requests/top-endpoints', { params: { hours, sort_by: sortBy, limit, service } })
export const getRequestTimeline = (hours = 24, service?: string) =>
  api.get('/requests/timeline', { params: { hours, service } })
export const getSlowRequests = (hours = 24, thresholdMs = 1000, limit = 50) =>
  api.get('/requests/slow', { params: { hours, threshold_ms: thresholdMs, limit } })

// --- Errors ---
export const getErrorSummary = (hours = 24, service?: string) =>
  api.get('/errors/summary', { params: { hours, service } })
export const getErrorList = (params: {
  hours?: number; service?: string; severity?: string;
  error_type?: string; page?: number; page_size?: number
}) => api.get('/errors/list', { params })
export const getErrorGroups = (params: {
  status?: string; service?: string; severity?: string;
  sort_by?: string; limit?: number
}) => api.get('/errors/groups', { params })
export const updateErrorGroupStatus = (groupId: number, newStatus: string) =>
  api.put(`/errors/groups/${groupId}/status`, null, { params: { new_status: newStatus } })
export const getErrorTimeline = (hours = 24, service?: string) =>
  api.get('/errors/timeline', { params: { hours, service } })
export const getErrorTypeStats = (hours = 24, service?: string) =>
  api.get('/errors/types', { params: { hours, service } })

// --- Integration ---
export const createGithubIssue = (groupId: number) =>
  api.post(`/integration/github-issue/${groupId}`)
export const pushToQaDashboard = (status = 'open', severity?: string) =>
  api.post('/integration/qa-dashboard', null, { params: { status, severity } })
export const reportToStandup = () =>
  api.post('/integration/standup')

// --- Health ---
export const getHealth = () => api.get('/health')

export default api
