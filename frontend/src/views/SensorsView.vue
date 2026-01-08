<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useSensorStore, type Sensor } from '../stores/sensors'
import { api } from '../api'

const sensorStore = useSensorStore()

const showModal = ref(false)
const editingSensor = ref<Sensor | null>(null)
const formData = ref({
  name: '',
  description: '',
  protocol: 'MODBUS_TCP',
  connection_params: {} as Record<string, unknown>,
  data_formula: 'val',
  unit: '',
  poll_interval_ms: 1000,
})

const protocols = [
  { value: 'MODBUS_TCP', label: 'Modbus TCP' },
  { value: 'MODBUS_RTU', label: 'Modbus RTU' },
  { value: 'MQTT', label: 'MQTT' },
  { value: 'CAN', label: 'CANbus' },
]

// Connection params based on protocol
const connectionFields = {
  MODBUS_TCP: [
    { key: 'host', label: 'Host IP', type: 'text', default: '192.168.1.10' },
    { key: 'port', label: 'Port', type: 'number', default: 502 },
    { key: 'slave_id', label: 'Slave ID', type: 'number', default: 1 },
    { key: 'address', label: 'Register Address', type: 'number', default: 40001 },
  ],
  MODBUS_RTU: [
    { key: 'port', label: 'Serial Port', type: 'text', default: '/dev/ttyUSB0' },
    { key: 'baudrate', label: 'Baudrate', type: 'number', default: 9600 },
    { key: 'slave_id', label: 'Slave ID', type: 'number', default: 1 },
    { key: 'address', label: 'Register Address', type: 'number', default: 40001 },
  ],
  MQTT: [
    { key: 'broker', label: 'Broker', type: 'text', default: 'localhost' },
    { key: 'port', label: 'Port', type: 'number', default: 1883 },
    { key: 'topic', label: 'Topic', type: 'text', default: 'sensors/temp1' },
    { key: 'json_path', label: 'JSON Path', type: 'text', default: '$.value' },
  ],
  CAN: [
    { key: 'interface', label: 'Interface', type: 'text', default: 'socketcan' },
    { key: 'channel', label: 'Channel', type: 'text', default: 'can0' },
    { key: 'arbitration_id', label: 'Arbitration ID', type: 'text', default: '0x123' },
    { key: 'signal_name', label: 'Signal Name', type: 'text', default: '' },
  ],
}

onMounted(() => {
  sensorStore.fetchSensors()
})

function openAddModal() {
  editingSensor.value = null
  formData.value = {
    name: '',
    description: '',
    protocol: 'MODBUS_TCP',
    connection_params: {},
    data_formula: 'val',
    unit: '',
    poll_interval_ms: 1000,
  }
  initConnectionParams('MODBUS_TCP')
  showModal.value = true
}

function openEditModal(sensor: Sensor) {
  editingSensor.value = sensor
  formData.value = {
    name: sensor.name,
    description: sensor.description || '',
    protocol: sensor.protocol,
    connection_params: { ...sensor.connection_params },
    data_formula: sensor.data_formula,
    unit: sensor.unit || '',
    poll_interval_ms: sensor.poll_interval_ms,
  }
  showModal.value = true
}

function initConnectionParams(protocol: string) {
  const fields = connectionFields[protocol as keyof typeof connectionFields] || []
  formData.value.connection_params = {}
  fields.forEach(f => {
    formData.value.connection_params[f.key] = f.default
  })
}

function handleProtocolChange() {
  initConnectionParams(formData.value.protocol)
}

async function handleSubmit() {
  if (editingSensor.value) {
    await sensorStore.updateSensor(editingSensor.value.id, formData.value)
  } else {
    await sensorStore.createSensor(formData.value)
  }
  showModal.value = false
}

async function handleDelete(sensor: Sensor) {
  if (confirm(`Delete sensor "${sensor.name}"?`)) {
    await sensorStore.deleteSensor(sensor.id)
  }
}

async function testFormula() {
  try {
    const response = await api.post('/api/sensors/test-formula', {
      formula: formData.value.data_formula,
      test_value: 100,
    })
    alert(`Formula result: ${response.data.result}`)
  } catch (e) {
    alert('Invalid formula')
  }
}

function getStatusClass(status: string): string {
  switch (status) {
    case 'ONLINE': return 'online'
    case 'OFFLINE': return 'offline'
    case 'ERROR': return 'warning'
    default: return 'unknown'
  }
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Sensors</h1>
      <button class="btn btn-primary" @click="openAddModal">
        <i class="pi pi-plus"></i>
        Add Sensor
      </button>
    </div>

    <div class="sensor-list">
      <div 
        v-for="sensor in sensorStore.sensors" 
        :key="sensor.id" 
        class="sensor-item"
        style="cursor: pointer;"
        @click="openEditModal(sensor)"
      >
        <div :class="['sensor-status', getStatusClass(sensor.status)]"></div>
        <div class="sensor-info" style="flex: 2;">
          <div class="sensor-name">{{ sensor.name }}</div>
          <div class="sensor-protocol">{{ sensor.protocol }} • {{ sensor.description || 'No description' }}</div>
        </div>
        <div style="flex: 1; text-align: center;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">Formula</div>
          <code style="font-size: 0.875rem;">{{ sensor.data_formula }}</code>
        </div>
        <div class="sensor-value">
          <div class="sensor-reading">{{ sensor.last_value?.toFixed(2) || '--' }}</div>
          <div class="sensor-unit">{{ sensor.unit || '' }}</div>
        </div>
        <button 
          class="btn btn-secondary" 
          style="padding: 0.5rem 0.75rem;"
          @click.stop="handleDelete(sensor)"
        >
          <i class="pi pi-trash"></i>
        </button>
      </div>
    </div>

    <!-- Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ editingSensor ? 'Edit Sensor' : 'Add Sensor' }}</h2>
          <button class="btn-close" @click="showModal = false">
            <i class="pi pi-times"></i>
          </button>
        </div>

        <form @submit.prevent="handleSubmit" class="modal-body">
          <div class="form-row">
            <div class="form-group" style="flex: 2;">
              <label class="form-label">Name *</label>
              <input v-model="formData.name" type="text" class="form-input" required />
            </div>
            <div class="form-group" style="flex: 1;">
              <label class="form-label">Protocol *</label>
              <select 
                v-model="formData.protocol" 
                class="form-input"
                @change="handleProtocolChange"
                :disabled="!!editingSensor"
              >
                <option v-for="p in protocols" :key="p.value" :value="p.value">
                  {{ p.label }}
                </option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Description</label>
            <input v-model="formData.description" type="text" class="form-input" />
          </div>

          <h3 style="margin: 1rem 0 0.75rem; font-size: 0.875rem; color: var(--text-muted);">
            Connection Parameters
          </h3>

          <div class="form-row">
            <div 
              v-for="field in connectionFields[formData.protocol as keyof typeof connectionFields]"
              :key="field.key"
              class="form-group"
              style="flex: 1;"
            >
              <label class="form-label">{{ field.label }}</label>
              <input 
                v-model="formData.connection_params[field.key]"
                :type="field.type"
                class="form-input"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group" style="flex: 2;">
              <label class="form-label">Data Formula</label>
              <div style="display: flex; gap: 0.5rem;">
                <input v-model="formData.data_formula" type="text" class="form-input" />
                <button type="button" class="btn btn-secondary" @click="testFormula">Test</button>
              </div>
            </div>
            <div class="form-group" style="flex: 1;">
              <label class="form-label">Unit</label>
              <input v-model="formData.unit" type="text" class="form-input" placeholder="°C, bar, %" />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Poll Interval (ms)</label>
            <input v-model.number="formData.poll_interval_ms" type="number" class="form-input" min="100" max="60000" />
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary">
              {{ editingSensor ? 'Save Changes' : 'Create Sensor' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--surface);
  border-radius: 16px;
  border: 1px solid var(--border);
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border);
}

.modal-header h2 {
  font-size: 1.25rem;
  font-weight: 600;
}

.btn-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.5rem;
}

.modal-body {
  padding: 1.5rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}

.form-row {
  display: flex;
  gap: 1rem;
}

@media (max-width: 600px) {
  .form-row {
    flex-direction: column;
  }
}
</style>
