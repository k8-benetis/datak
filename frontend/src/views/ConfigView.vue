<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api'

const deviceProfile = ref<object | null>(null)
const bufferStatus = ref({ unsynced_count: 0, synced_count: 0, cloud_available: true })
const loading = ref(false)

onMounted(async () => {
  await Promise.all([
    fetchDeviceProfile(),
    fetchBufferStatus(),
  ])
})

async function fetchDeviceProfile() {
  try {
    const response = await api.get('/api/config/device-profile')
    deviceProfile.value = response.data
  } catch (e) {
    console.error('Failed to fetch device profile:', e)
  }
}

async function fetchBufferStatus() {
  try {
    const response = await api.get('/api/config/buffer/status')
    bufferStatus.value = response.data
  } catch (e) {
    console.error('Failed to fetch buffer status:', e)
  }
}

async function flushBuffer() {
  loading.value = true
  try {
    const response = await api.post('/api/config/buffer/flush')
    alert(`Flushed ${response.data.synced} readings`)
    await fetchBufferStatus()
  } catch (e) {
    alert('Flush failed')
  } finally {
    loading.value = false
  }
}

function downloadProfile() {
  window.open('/api/config/device-profile/download', '_blank')
}

async function exportConfig() {
  try {
    const response = await api.get('/api/config/export')
    const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'gateway-config.json'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert('Export failed')
  }
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Configuration</h1>
    </div>

    <div class="config-grid">
      <!-- Device Profile -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">Device Profile</h2>
          <button class="btn btn-primary" @click="downloadProfile">
            <i class="pi pi-download"></i>
            Download JSON
          </button>
        </div>
        <p style="color: var(--text-muted); margin-bottom: 1rem;">
          Export the device profile to configure your Digital Twin platform.
        </p>
        <div v-if="deviceProfile" class="code-block">
          <pre>{{ JSON.stringify(deviceProfile, null, 2).slice(0, 500) }}...</pre>
        </div>
      </div>

      <!-- Buffer Status -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">Store & Forward Buffer</h2>
          <button 
            class="btn btn-secondary" 
            @click="flushBuffer"
            :disabled="loading || bufferStatus.unsynced_count === 0"
          >
            <i :class="['pi', loading ? 'pi-spin pi-spinner' : 'pi-sync']"></i>
            Flush Now
          </button>
        </div>
        
        <div class="buffer-stats">
          <div class="buffer-stat">
            <div class="stat-value">{{ bufferStatus.unsynced_count }}</div>
            <div class="stat-label">Pending Sync</div>
          </div>
          <div class="buffer-stat">
            <div class="stat-value">{{ bufferStatus.synced_count }}</div>
            <div class="stat-label">Synced</div>
          </div>
          <div class="buffer-stat">
            <div :class="['status-badge', bufferStatus.cloud_available ? 'success' : 'warning']">
              {{ bufferStatus.cloud_available ? 'Connected' : 'Buffering' }}
            </div>
            <div class="stat-label">Cloud Status</div>
          </div>
        </div>
      </div>

      <!-- Export/Import -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">Configuration Backup</h2>
        </div>
        <p style="color: var(--text-muted); margin-bottom: 1rem;">
          Export your current configuration for backup or migration.
        </p>
        <div style="display: flex; gap: 0.75rem;">
          <button class="btn btn-primary" @click="exportConfig">
            <i class="pi pi-download"></i>
            Export Config
          </button>
          <button class="btn btn-secondary" disabled>
            <i class="pi pi-upload"></i>
            Import Config
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.config-grid {
  display: grid;
  gap: 1.5rem;
}

.code-block {
  background: var(--background);
  border-radius: 8px;
  padding: 1rem;
  overflow-x: auto;
}

.code-block pre {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin: 0;
}

.buffer-stats {
  display: flex;
  gap: 2rem;
}

.buffer-stat {
  text-align: center;
}

.buffer-stat .stat-value {
  font-size: 1.5rem;
  font-weight: 700;
}

.buffer-stat .stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.status-badge {
  display: inline-block;
  padding: 0.375rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-badge.success {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.status-badge.warning {
  background: rgba(234, 179, 8, 0.15);
  color: var(--warning);
}
</style>
