<script setup>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'
import Swal from 'sweetalert2'

// --- CONFIGURACIÓN ESTÉTICA (COLORES PROFESIONALES) ---
const COLORS = {
  primary: '#2563eb',    // Azul Real moderno
  danger: '#dc2626',     // Rojo menos saturado
  success: '#059669',    // Verde Esmeralda
  warning: '#d97706',    // Ámbar
  cancel: '#64748b',     // Gris Azulado (Slate)
  background: '#f8fafc'  // Fondo muy claro
}

// --- ESTADO ---
const allocations = ref([])
const users = ref([])
const currentUser = ref(null)
const selectedOffer = ref(null)
const loading = ref(true)
const pendingRequests = ref([])
const workstations = ref([])

const days = [
  '2026-02-02', '2026-02-03', '2026-02-04', '2026-02-05', '2026-02-06',
  '2026-02-09', '2026-02-10', '2026-02-11', '2026-02-12', '2026-02-13',
  '2026-02-16', '2026-02-17', '2026-02-18', '2026-02-19', '2026-02-20',
  '2026-02-23', '2026-02-24', '2026-02-25', '2026-02-26', '2026-02-27'
]

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
// --- API ---
const fetchData = async () => {
  try {
    loading.value = true
    const resAlloc = await axios.get(`${API_URL}/allocations`)
    allocations.value = resAlloc.data
    workstations.value = [...new Set(resAlloc.data.map(a => a.workstation))].sort((a, b) => a - b)

    const resUsers = await axios.get(`${API_URL}/users`)
    users.value = resUsers.data.sort((a, b) => a.full_name.localeCompare(b.full_name))

    if (!currentUser.value && users.value.length > 0) currentUser.value = users.value[0].id

    await fetchNotifications()

  } catch (error) {
    console.error(error)
    Swal.fire({
      icon: 'error',
      title: 'Error de Conexión',
      text: 'No se pudo contactar al servidor.',
      confirmButtonColor: COLORS.primary
    })
  } finally {
    loading.value = false
  }
}

const fetchNotifications = async () => {
  if (!currentUser.value) return
  try {
    const res = await axios.get(`http://localhost:8000/pending-requests/${currentUser.value}`)
    pendingRequests.value = res.data
  } catch (e) { console.error(e) }
}

// --- UTILIDADES ---
const getAllocation = (puesto, fecha) => allocations.value.find(a => a.workstation === puesto && a.date === fecha)
const getUserNameById = (id) => { const u = users.value.find(user => user.id === id); return u ? u.full_name : '' }
const formatDate = (dateStr) => { const [year, month, day] = dateStr.split('-'); return `${day}/${month}` }

const getCellClass = (alloc) => {
  if (!alloc) return 'cell empty'
  if (selectedOffer.value && selectedOffer.value.id === alloc.id) return 'cell selected-offer'
  if (currentUser.value && alloc.user === getUserNameById(currentUser.value)) return 'cell my-shift'
  return 'cell occupied'
}

// --- INTERACCIÓN MEJORADA ---
const handleCellClick = async (alloc) => {
  // 1. Identificación requerida
  if (!currentUser.value) {
    return Swal.fire({
      icon: 'info',
      title: 'Identificación Necesaria',
      text: 'Por favor, selecciona quién eres en el menú superior.',
      confirmButtonColor: COLORS.primary,
      confirmButtonText: 'Entendido'
    })
  }
  if (!alloc) return

  const myName = getUserNameById(currentUser.value)

  // A. Clic en mi propio turno
  if (alloc.user === myName) {
    if (selectedOffer.value && selectedOffer.value.id === alloc.id) {
      selectedOffer.value = null
    } else {
      selectedOffer.value = alloc
      // Toast elegante
      const Toast = Swal.mixin({
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        background: '#fff',
        color: '#334155'
      })
      Toast.fire({
        icon: 'success',
        title: 'Oferta seleccionada'
      })
    }
    return
  }

  // B. Clic en turno ajeno sin oferta
  if (!selectedOffer.value) {
    return Swal.fire({
      icon: 'warning',
      title: 'Selecciona tu oferta',
      text: 'Primero debes hacer clic en uno de TUS turnos (verde) para ofrecerlo a cambio.',
      confirmButtonColor: COLORS.warning
    })
  }

  // C. CONFIRMACIÓN ESTILIZADA
  const result = await Swal.fire({
    title: 'Proponer Intercambio',
    html: `
      <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; text-align: left; font-size: 14px; color: #334155;">
        <div style="margin-bottom: 10px;">
          <span style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: bold;">Tú entregas:</span><br>
          <span style="font-weight: 600; font-size: 16px;">📅 ${formatDate(selectedOffer.value.date)}</span> 
          <span style="color: #64748b;">(Puesto #${selectedOffer.value.workstation})</span>
        </div>
        <div style="border-top: 1px dashed #cbd5e1; margin: 10px 0;"></div>
        <div>
          <span style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: bold;">Recibes de ${alloc.user}:</span><br>
          <span style="font-weight: 600; font-size: 16px; color: #2563eb;">📅 ${formatDate(alloc.date)}</span>
          <span style="color: #64748b;">(Puesto #${alloc.workstation})</span>
        </div>
      </div>
    `,
    showCancelButton: true,
    confirmButtonColor: COLORS.primary,
    cancelButtonColor: COLORS.cancel,
    confirmButtonText: 'Enviar Propuesta',
    cancelButtonText: 'Cancelar',
    reverseButtons: true, // Botón de acción a la derecha (estilo Windows/Web moderno)
    focusConfirm: false
  })

  if (result.isConfirmed) {
    try {
      const response = await axios.post('http://localhost:8000/request-swap', {
        requester_id: currentUser.value,
        offer_allocation_id: selectedOffer.value.id,
        target_allocation_id: alloc.id
      })

      Swal.fire({
        title: '¡Enviado!',
        text: response.data.message,
        icon: 'success',
        confirmButtonColor: COLORS.success
      })
      selectedOffer.value = null

    } catch (error) {
      const msg = error.response ? error.response.data.detail : "Error de conexión"
      Swal.fire({ title: 'Error', text: msg, icon: 'error', confirmButtonColor: COLORS.danger })
    }
  }
}

const handleResponse = async (reqId, action) => {
  try {
    if (action === 'REJECT') {
      const result = await Swal.fire({
        title: '¿Rechazar solicitud?',
        text: "Esta acción no se puede deshacer.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: COLORS.danger,
        cancelButtonColor: COLORS.cancel,
        confirmButtonText: 'Sí, rechazar'
      })
      if (!result.isConfirmed) return
    }

    await axios.post('http://localhost:8000/process-swap', { request_id: reqId, action: action })

    Swal.fire({
      icon: 'success',
      title: action === 'ACCEPT' ? 'Intercambio Exitoso' : 'Rechazado',
      showConfirmButton: false,
      timer: 1500,
      timerProgressBar: true
    })

    await fetchData()
  } catch (error) {
    Swal.fire('Error', 'No se pudo procesar la solicitud', 'error')
  }
}

watch(currentUser, () => { selectedOffer.value = null; fetchNotifications() })
onMounted(() => fetchData())
</script>

<template>
  <div class="container">
    <header>
      <div class="header-left">
        <h1>📅 Planificación <span class="subtitle">Febrero 2026</span></h1>
      </div>
      <div class="header-right">
        <div class="user-info" v-if="selectedOffer">
          <span class="offer-badge">Oferta: {{ formatDate(selectedOffer.date) }}</span>
        </div>
        <div class="user-select-wrapper">
          <label>Usuario:</label>
          <select v-model="currentUser">
            <option v-for="u in users" :key="u.id" :value="u.id">{{ u.full_name }}</option>
          </select>
        </div>
        <button class="refresh-btn" @click="fetchData" title="Actualizar datos">🔄</button>
      </div>
    </header>

    <div v-if="pendingRequests.length > 0" class="notifications-panel">
      <div class="notif-header">
        <h3>🔔 Notificaciones Pendientes</h3>
        <span class="badge-count">{{ pendingRequests.length }}</span>
      </div>
      <div v-for="req in pendingRequests" :key="req.id" class="notification-card">
        <div class="notif-content">
          <div class="notif-user">👤 {{ req.requester_name }} propone cambio:</div>
          <div class="notif-dates">
            Entrega el <span class="date-tag in">{{ formatDate(req.requester_date) }}</span>
            ⟷ Pide tu <span class="date-tag out">{{ formatDate(req.my_date) }}</span>
          </div>
        </div>
        <div class="notif-actions">
          <button class="btn-action accept" @click="handleResponse(req.id, 'ACCEPT')">Aceptar</button>
          <button class="btn-action reject" @click="handleResponse(req.id, 'REJECT')">Rechazar</button>
        </div>
      </div>
    </div>

    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th class="sticky-col">Puesto</th>
            <th v-for="day in days" :key="day">{{ formatDate(day) }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ws in workstations" :key="ws">
            <td class="sticky-col font-bold">#{{ ws }}</td>
            <td v-for="day in days" :key="day" class="cell-container">
              <div v-if="getAllocation(ws, day)" :class="getCellClass(getAllocation(ws, day))"
                @click="handleCellClick(getAllocation(ws, day))">
                {{ getAllocation(ws, day).user }}
              </div>
              <div v-else class="cell empty"></div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style>
/* IMPORTAMOS FUENTE 'INTER' */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ESTILOS GLOBALES */
body {
  margin: 0;
  background-color: #f1f5f9;
}

.container {
  font-family: 'Inter', sans-serif;
  padding: 30px;
  min-height: 100vh;
  color: #1e293b;
  max-width: 100%;
  box-sizing: border-box;
}

/* HEADER */
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
  background: #ffffff;
  padding: 15px 25px;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

h1 {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 10px;
}

.subtitle {
  font-weight: 400;
  color: #64748b;
  font-size: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.user-select-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #475569;
}

select {
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  font-family: 'Inter', sans-serif;
  color: #334155;
  outline: none;
  transition: border-color 0.2s;
}

select:focus {
  border-color: #2563eb;
}

.refresh-btn {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 16px;
}

.refresh-btn:hover {
  background: #e2e8f0;
  transform: rotate(15deg);
}

/* TABLA */
.table-wrapper {
  overflow-x: auto;
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

table {
  border-collapse: separate;
  border-spacing: 0;
  width: 100%;
  min-width: 1400px;
}

th,
td {
  border-bottom: 1px solid #e2e8f0;
  border-right: 1px solid #e2e8f0;
  padding: 0;
  text-align: center;
  height: 44px;
  font-size: 13px;
}

th {
  background-color: #f8fafc;
  padding: 12px;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 11px;
}

/* COLUMNA FIJA */
.sticky-col {
  position: sticky;
  left: 0;
  background-color: #ffffff;
  z-index: 10;
  border-right: 2px solid #e2e8f0;
  width: 80px;
  box-shadow: 2px 0 5px rgba(0, 0, 0, 0.02);
}

th.sticky-col {
  background-color: #f8fafc;
  z-index: 20;
}

/* CELDAS */
.cell {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.1s;
  padding: 0 8px;
  box-sizing: border-box;
  font-weight: 500;
  color: #334155;
}

.cell.occupied:hover {
  background-color: #eff6ff;
  color: #2563eb;
}

.cell.my-shift {
  background-color: #dcfce7;
  color: #15803d;
  font-weight: 600;
  box-shadow: inset 0 0 0 1px #86efac;
}

/* Verde moderno */
.cell.selected-offer {
  background-color: #fffbeb;
  color: #b45309;
  font-weight: 700;
  box-shadow: inset 0 0 0 2px #fcd34d;
  animation: pulse 2s infinite;
}

.cell.empty {
  background: #f8fafc;
  /* Patrón rayado sutil */
  background-image: linear-gradient(45deg, #f1f5f9 25%, transparent 25%, transparent 50%, #f1f5f9 50%, #f1f5f9 75%, transparent 75%, transparent);
  background-size: 10px 10px;
}

@keyframes pulse {
  0% {
    background-color: #fffbeb;
  }

  50% {
    background-color: #fef3c7;
  }

  100% {
    background-color: #fffbeb;
  }
}

/* NOTIFICACIONES */
.notifications-panel {
  background-color: #fff7ed;
  border: 1px solid #ffedd5;
  padding: 20px;
  margin-bottom: 25px;
  border-radius: 10px;
}

.notif-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.notif-header h3 {
  margin: 0;
  color: #9a3412;
  font-size: 15px;
  font-weight: 600;
}

.badge-count {
  background: #c2410c;
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;
}

.notification-card {
  background: white;
  padding: 15px;
  margin-bottom: 10px;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #fed7aa;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.notif-user {
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
  font-size: 14px;
}

.notif-dates {
  font-size: 13px;
  color: #64748b;
}

.date-tag {
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.date-tag.in {
  background: #dbeafe;
  color: #1e40af;
}

.date-tag.out {
  background: #fee2e2;
  color: #991b1b;
}

.btn-action {
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.1s;
  margin-left: 10px;
  font-family: 'Inter', sans-serif;
}

.btn-action:active {
  transform: scale(0.96);
}

.btn-action.accept {
  background: #2563eb;
  color: white;
  box-shadow: 0 2px 5px rgba(37, 99, 235, 0.3);
}

.btn-action.reject {
  background: white;
  color: #ef4444;
  border: 1px solid #fca5a5;
}

.btn-action.reject:hover {
  background: #fef2f2;
}

.offer-badge {
  background: #fff7ed;
  color: #c2410c;
  border: 1px solid #ffedd5;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

/* SWEETALERT OVERRIDES (CSS PROFESIONAL) */
div:where(.swal2-container) div:where(.swal2-popup) {
  border-radius: 16px !important;
  font-family: 'Inter', sans-serif !important;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
}

div:where(.swal2-title) {
  color: #1e293b !important;
  font-weight: 700 !important;
  font-size: 1.5em !important;
}

div:where(.swal2-html-container) {
  color: #475569 !important;
  font-size: 1.05em !important;
}

div:where(.swal2-actions) button {
  box-shadow: none !important;
  border-radius: 8px !important;
  font-weight: 500 !important;
  padding: 10px 24px !important;
}
</style>