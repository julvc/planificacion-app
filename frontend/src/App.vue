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
  const { value: secretCode } = await Swal.fire({
    title: 'Seguridad Requerida',
    input: 'text',
    inputLabel: 'Crea una palabra clave para este cambio',
    inputPlaceholder: 'Ej: 1234, PIZZA, GOKU',
    html: `Tú entregas: <b>${formatDate(selectedOffer.value.date)}</b><br>Recibes: <b>${formatDate(alloc.date)}</b>`,
    showCancelButton: true,
    confirmButtonText: 'Enviar Solicitud',
    inputValidator: (value) => {
      if (!value) {
        return '¡Debes escribir un código!'
      }
    }
  })

  if (secretCode) {
    // 1. Sanitizar entrada (quitar espacios al inicio/final)
    const codeToSend = secretCode.trim()

    try {
      // 2. Mostrar "Cargando..." antes de enviar (UX)
      Swal.fire({
        title: 'Enviando solicitud...',
        text: 'Por favor espera',
        allowOutsideClick: false,
        didOpen: () => {
          Swal.showLoading() // Activa el spinner
        }
      })

      // 3. Petición al Backend
      await axios.post(`${API_URL}/request-swap`, {
        requester_id: currentUser.value,
        offer_allocation_id: selectedOffer.value.id,
        target_allocation_id: alloc.id,
        verification_code: codeToSend
      })

      // 4. Éxito: Mostrar el código en GRANDE para que no se olvide
      await Swal.fire({
        icon: 'success',
        title: '¡Solicitud Enviada!',
        html: `
        <div style="text-align: center;">
          <p class="mb-2">Dile a tu compañero que la clave secreta es:</p>
          <div style="
            background: #eff6ff; 
            color: #1d4ed8; 
            font-size: 28px; 
            font-weight: 800; 
            padding: 15px; 
            border-radius: 8px; 
            border: 2px dashed #93c5fd;
            margin: 10px 0;
            letter-spacing: 2px;
          ">
            ${codeToSend}
          </div>
          <small style="color: #6b7280;">Sin este código, no podrán aceptar el cambio.</small>
        </div>
      `,
        confirmButtonText: 'Entendido, copiado',
        confirmButtonColor: COLORS.success
      })

      // 5. Limpieza de estado
      selectedOffer.value = null

    } catch (error) {
      // 6. Manejo de Errores Robusto
      // Si el backend envía un mensaje específico (ej: 400, 404), lo mostramos.
      const errorMsg = error.response?.data?.detail || "No se pudo enviar la solicitud. Revisa tu conexión.";

      Swal.fire({
        icon: 'error',
        title: 'Hubo un problema',
        text: errorMsg,
        confirmButtonColor: COLORS.danger
      })
    }
  }

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
  let codeInput = ""

  // Si es ACEPTAR, pedimos el código
  if (action === 'ACCEPT') {
    const { value: code } = await Swal.fire({
      title: 'Código de Seguridad',
      input: 'text',
      inputLabel: 'Ingresa la clave que te dio tu compañero',
      inputPlaceholder: 'Clave secreta...',
      showCancelButton: true,
      inputValidator: (value) => {
        if (!value) return 'El código es obligatorio'
      }
    })

    if (!code) return // Si canceló
    codeInput = code
  }
  // Si es REJECT, confirmación simple
  else {
    const res = await Swal.fire({ title: '¿Rechazar?', showCancelButton: true, confirmButtonText: 'Sí' })
    if (!res.isConfirmed) return
  }

  try {
    await axios.post(`${API_URL}/process-swap`, {
      request_id: reqId,
      action: action,
      verification_code: codeInput // Enviamos lo que escribió (o vacío si rechazó)
    })
    Swal.fire('Éxito', action === 'ACCEPT' ? '¡Cambio Realizado!' : 'Rechazado', 'success')
    await fetchData()
  } catch (error) {
    Swal.fire('Error', error.response?.data?.detail || 'Código incorrecto', 'error')
  }
}

watch(currentUser, () => { selectedOffer.value = null; fetchNotifications() })
onMounted(() => fetchData())
</script>

<template>
  <div class="rotate-warning">
    <div class="rotate-content">
      <div class="rotate-icon">📱🔄</div>
      <h3>Gira tu teléfono</h3>
      <p>La planificación es muy ancha para verla en vertical.</p>
    </div>
  </div>
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

/* =========================================
   RESPONSIVE DESIGN (MÓVILES)
   ========================================= */

/* 1. ESTILOS GENERALES PARA PANTALLAS PEQUEÑAS */
@media (max-width: 900px) {
  .container {
    padding: 10px;
    /* Menos relleno */
    max-width: 100vw;
  }

  /* Header más compacto */
  header {
    flex-direction: column;
    /* Apilar elementos si es necesario */
    align-items: stretch;
    gap: 10px;
    padding: 10px;
  }

  .header-left h1 {
    font-size: 18px;
    /* Título más pequeño */
  }

  .subtitle {
    display: none;
    /* Ocultar subtítulo para ahorrar espacio */
  }

  .header-right {
    justify-content: space-between;
    width: 100%;
  }

  /* Ajustar botones y selects para dedos (Touch targets) */
  select,
  .refresh-btn {
    padding: 10px;
    font-size: 16px;
    /* Evita zoom automático en iPhone */
  }

  /* TABLA: Ajustes críticos */
  th,
  td {
    height: 50px;
    /* Celdas más altas para dedos gordos */
    min-width: 60px;
    /* Ancho mínimo por día */
    font-size: 12px;
  }

  .sticky-col {
    width: 60px;
    /* Puesto más angosto */
    font-size: 11px;
    padding: 0 5px;
  }

  /* Notificaciones más compactas */
  .notification-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .notif-actions {
    width: 100%;
    display: flex;
    justify-content: flex-end;
  }
}

/* 2. PANTALLA DE "GIRA TU TELÉFONO" (Solo Vertical) */
.rotate-warning {
  display: none;
  /* Oculto por defecto */
}

@media (max-width: 900px) and (orientation: portrait) {
  .rotate-warning {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: #1e293b;
    z-index: 9999;
    display: flex;
    justify-content: center;
    align-items: center;
    color: white;
    text-align: center;
  }

  .rotate-content {
    padding: 20px;
  }

  .rotate-icon {
    font-size: 60px;
    margin-bottom: 20px;
    animation: spin 2s infinite;
  }

  .container {
    display: none;
    /* Oculta la app de fondo */
  }
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  25% {
    transform: rotate(-90deg);
  }

  100% {
    transform: rotate(-90deg);
  }
}

/* 3. MODO PAISAJE (LANDSCAPE) - La vista óptima */
@media (max-width: 900px) and (orientation: landscape) {
  .container {
    padding: 5px;
    /* Aprovechar cada pixel */
  }

  header {
    flex-direction: row;
    /* Volver a fila para ahorrar altura */
    padding: 8px;
    margin-bottom: 10px;
  }

  .header-left h1 {
    font-size: 16px;
  }

  .user-select-wrapper label {
    display: none;
    /* Ocultar texto "Usuario:" */
  }

  /* La tabla debe ocupar casi toda la altura */
  .table-wrapper {
    max-height: 80vh;
    /* Scroll vertical si hay muchos puestos */
  }
}
</style>