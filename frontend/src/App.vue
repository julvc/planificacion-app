<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

// --- ESTADO ---
const allocations = ref([])
const users = ref([])      // Lista de usuarios para el "Login"
const currentUser = ref(null) // Usuario seleccionado actual
const loading = ref(true)
const workstations = ref([])

// Fechas (Febrero)
const days = [
  '2026-02-02', '2026-02-03', '2026-02-04', '2026-02-05', '2026-02-06',
  '2026-02-09', '2026-02-10', '2026-02-11', '2026-02-12', '2026-02-13',
  '2026-02-16', '2026-02-17', '2026-02-18', '2026-02-19', '2026-02-20',
  '2026-02-23', '2026-02-24', '2026-02-25', '2026-02-26', '2026-02-27'
]

// --- API ---
const fetchData = async () => {
  try {
    loading.value = true
    // 1. Cargar Turnos
    const resAlloc = await axios.get('http://localhost:8000/allocations')
    allocations.value = resAlloc.data
    workstations.value = [...new Set(resAlloc.data.map(a => a.workstation))].sort((a,b) => a - b)

    // 2. Cargar Usuarios (Para el selector)
    const resUsers = await axios.get('http://localhost:8000/users')
    users.value = resUsers.data.sort((a, b) => a.full_name.localeCompare(b.full_name))
    
    // Auto-seleccionar el primero si no hay nadie
    if (!currentUser.value && users.value.length > 0) {
      currentUser.value = users.value[0].id
    }

  } catch (error) {
    console.error(error)
    alert("Error conectando al backend")
  } finally {
    loading.value = false
  }
}

// --- LOGICA VISUAL ---
const getAllocation = (puesto, fecha) => {
  return allocations.value.find(a => a.workstation === puesto && a.date === fecha)
}

const getCellClass = (alloc) => {
  if (!alloc) return 'cell empty'
  if (currentUser.value && alloc.user === getUserNameById(currentUser.value)) {
    return 'cell my-shift' // Resaltar mis turnos
  }
  return 'cell occupied'
}

const getUserNameById = (id) => {
  const u = users.value.find(user => user.id === id)
  return u ? u.full_name : ''
}

// --- INTERACCIÓN ---
// const handleCellClick = (alloc) => {
//   if (!currentUser.value) return alert("Selecciona un usuario arriba primero")
//   if (!alloc) return
  
//   const myName = getUserNameById(currentUser.value)

//   // 1. Si es mi propio turno
//   if (alloc.user === myName) {
//     alert(`Este es tu puesto (#${alloc.workstation}) para el día ${alloc.date}. No puedes intercambiar contigo mismo.`)
//     return
//   }

//   // 2. Si es de otro compañero
//   const confirmacion = confirm(`propuesta de INTERCAMBIO:\n\nTu: ${myName}\nCompañero: ${alloc.user}\nFecha: ${alloc.date}\n\n¿Quieres solicitar este cambio?`)
  
//   if (confirmacion) {
//     // AQUÍ LLAMAREMOS AL BACKEND LUEGO
//     console.log("Enviando solicitud al backend...", {
//       solicitante: currentUser.value,
//       receptor_turno_id: alloc.id,
//       fecha: alloc.date
//     })
//     alert("✅ Solicitud enviada (Simulación). El backend recibirá esto en el siguiente paso.")
//   }
// }

const handleCellClick = async (alloc) => {
  // 1. Validaciones previas locales
  if (!currentUser.value) return alert("Por favor selecciona quién eres en el menú superior.")
  if (!alloc) return
  
  const myName = getUserNameById(currentUser.value)

  if (alloc.user === myName) {
    alert(`Este es tu puesto (#${alloc.workstation}) del día. ¡Cuídalo!`)
    return
  }

  // 2. Confirmación de usuario
  const confirmacion = confirm(`PROPUESTA DE CAMBIO\n\n¿Quieres proponer a ${alloc.user} cambiar puestos el día ${alloc.date}?\n\n(Se descontará 1 crédito si aceptan)`)
  
  if (confirmacion) {
    try {
      // 3. Llamada al Backend
      const response = await axios.post('http://localhost:8000/request-swap', {
        requester_id: currentUser.value,
        target_allocation_id: alloc.id
      })

      // 4. Éxito
      alert(response.data.message)
      
    } catch (error) {
      // 5. Manejo de Errores (Créditos insuficientes, etc)
      if (error.response) {
        alert(`Error: ${error.response.data.detail}`)
      } else {
        alert("Error de conexión con el servidor")
      }
    }
  }
}


const formatDate = (dateStr) => {
  const [month, day] = dateStr.split('-')
  return `${day}/${month}`
}

onMounted(() => fetchData())
</script>

<template>
  <div class="container">
    <header>
      <div class="header-left">
        <h1>📅 Planificación</h1>
      </div>
      
      <div class="header-right">
        <label>Escoger desarrollador(a): </label>
        <select v-model="currentUser">
          <option v-for="u in users" :key="u.id" :value="u.id">{{ u.full_name }} ({{ u.swap_credits }} créditos)</option>
        </select>
        <button @click="fetchData">🔄 Refrescar</button>
      </div>
    </header>

    <div v-if="loading">Cargando...</div>

    <div class="table-wrapper" v-else>
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
              <div 
                v-if="getAllocation(ws, day)"
                :class="getCellClass(getAllocation(ws, day))"
                @click="handleCellClick(getAllocation(ws, day))"
              >
                {{ getAllocation(ws, day).user }}
              </div>
              <div v-else class="cell empty">-</div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style>
/* Estilos Base */
.container { font-family: 'Segoe UI', sans-serif; padding: 20px; background-color: #f4f6f8; min-height: 100vh; }
header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
select { padding: 8px; border-radius: 4px; border: 1px solid #ccc; margin-right: 10px; font-size: 14px; }
button { background: #3498db; border: none; padding: 8px 15px; color: white; border-radius: 4px; cursor: pointer; }
button:hover { background: #2980b9; }

/* Tabla */
.table-wrapper { overflow-x: auto; background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
table { border-collapse: separate; border-spacing: 0; width: 100%; min-width: 1400px; }
th, td { border: 1px solid #e0e0e0; padding: 0; text-align: center; font-size: 13px; height: 40px; } /* Padding 0 para que el div llene la celda */
th { background-color: #f8f9fa; padding: 10px; font-weight: 600; color: #555; }

/* Celdas Interactivas */
.cell { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; padding: 5px; box-sizing: border-box; }
.cell.occupied:hover { background-color: #e3f2fd; color: #1565c0; font-weight: bold; }
.cell.my-shift { background-color: #d4edda; color: #155724; border: 2px solid #c3e6cb; font-weight: bold; } /* Mis turnos en verde */
.cell.empty { color: #ccc; cursor: default; }

.sticky-col { position: sticky; left: 0; background-color: #fff; z-index: 2; border-right: 2px solid #ddd; width: 80px; }
</style>