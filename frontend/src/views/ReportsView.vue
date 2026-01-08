<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api'

interface Report {
  name: string
  path: string
  size_bytes: number
  modified: string
  compressed: boolean
}

const reports = ref<Report[]>([])
const loading = ref(false)

onMounted(async () => {
  await fetchReports()
})

async function fetchReports() {
  loading.value = true
  try {
    const response = await api.get('/api/config/reports')
    reports.value = response.data
  } catch (e) {
    console.error('Failed to fetch reports:', e)
  } finally {
    loading.value = false
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

function downloadReport(report: Report) {
  window.open(`/api/config/reports/${report.name}`, '_blank')
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Reports</h1>
      <button class="btn btn-secondary" @click="fetchReports">
        <i class="pi pi-refresh"></i>
        Refresh
      </button>
    </div>

    <div class="card">
      <div class="card-header">
        <h2 class="card-title">CSV Statistical Reports</h2>
        <span style="font-size: 0.875rem; color: var(--text-muted);">
          Auto-generated every 1/5/60 minutes
        </span>
      </div>

      <div v-if="loading" style="text-align: center; padding: 2rem;">
        <i class="pi pi-spin pi-spinner" style="font-size: 2rem;"></i>
      </div>

      <div v-else-if="reports.length === 0" style="text-align: center; padding: 2rem; color: var(--text-muted);">
        <i class="pi pi-file" style="font-size: 3rem; margin-bottom: 1rem;"></i>
        <p>No reports generated yet</p>
      </div>

      <table v-else class="reports-table">
        <thead>
          <tr>
            <th>File Name</th>
            <th>Size</th>
            <th>Generated</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="report in reports" :key="report.name">
            <td>
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i :class="['pi', report.compressed ? 'pi-file-zip' : 'pi-file']"></i>
                {{ report.name }}
              </div>
            </td>
            <td>{{ formatSize(report.size_bytes) }}</td>
            <td>{{ formatDate(report.modified) }}</td>
            <td>
              <button class="btn btn-secondary" style="padding: 0.375rem 0.75rem;" @click="downloadReport(report)">
                <i class="pi pi-download"></i>
                Download
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.reports-table {
  width: 100%;
  border-collapse: collapse;
}

.reports-table th,
.reports-table td {
  padding: 0.875rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
}

.reports-table th {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
}

.reports-table tr:hover {
  background: var(--surface-hover);
}
</style>
