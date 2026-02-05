/* --- Secure Exit Logic --- */
const modal = document.getElementById('secureExitModal');
const passInput = document.getElementById('adminPass');

function toggleModal(show) {
  if (show) {
    modal.classList.add('active');
    passInput.value = '';
    // Forzar foco agresivamente
    setTimeout(() => {
      passInput.focus();
      passInput.select();
    }, 100);
  } else {
    modal.classList.remove('active');
    // Devolver foco al scan input principal
    setTimeout(() => document.getElementById('scan-input').focus(), 100);
  }
}

async function verifyExit() {
  const pwd = passInput.value;
  if (!pwd) return;

  try {
    const res = await fetch('/api/admin/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pwd })
    });
    const data = await res.json();

    if (data.ok) {
      window.location.href = '/';
    } else {
      alert("Contraseña incorrecta");
      passInput.value = '';
      passInput.focus();
    }
  } catch (e) {
    console.error(e);
    alert("Error de conexión");
  }
}

// Allow Enter key in modal
if (passInput) {
    passInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') verifyExit();
    });
}

// --- Main App Logic ---

// Elementos DOM
const scanInput = document.getElementById('scan-input');
const mainCard = document.getElementById('main-card');
const resultArea = document.getElementById('result-area');
const counterVal = document.getElementById('counter-val');
const clockEl = document.getElementById('clock');
const placeholderContent = document.getElementById('placeholder-anim') ? document.getElementById('placeholder-anim').outerHTML : '';

// Estado local
let resetTimer = null;

// --- Reloj ---
function updateClock() {
  const now = new Date();
  if(clockEl) clockEl.textContent = now.toLocaleTimeString('es-PE', { hour12: false });
}
if(clockEl) {
    setInterval(updateClock, 1000);
    updateClock();
}

// --- Audio Feedback ---
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function playSound(type) {
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.connect(gain);
  gain.connect(audioCtx.destination);

  if (type === 'success') {
    // Ding: High pitch sine wave
    osc.type = 'sine';
    osc.frequency.setValueAtTime(1000, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(500, audioCtx.currentTime + 0.5);
    gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.5);
  } else if (type === 'error') {
    // Buzz: Low pitch sawtooth
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(150, audioCtx.currentTime);
    osc.frequency.linearRampToValueAtTime(100, audioCtx.currentTime + 0.3);
    gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.3);
  }
}

// --- Lógica de Negocio ---

// Función para procesar el código escaneado
async function processCode(code) {
  if (!code) return;

  // Mostrar estado de carga (opcional, aquí es muy rápido)
  resultArea.innerHTML = `<div style="color:var(--text-sub);">Procesando...</div>`;

  try {
    const response = await fetch(API_INGRESO, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ piso: PISO_ID, codigo: code })
    });
    const data = await response.json();
    renderResult(data);
  } catch (error) {
    console.error("Error de red:", error);
    playSound('error');
    renderError("Error de conexión con el servidor.");
  }

  // Refrescar contador inmediatamente
  fetchCounter();
}

// Renderizar respuesta exitosa o bloqueo de lógica de negocio
function renderResult(data) {
  clearTimeout(resetTimer);

  let html = '';
  let statusClass = '';

  if (data.ok) {
    playSound('success');
    // Ingreso Exitoso
    statusClass = 'status-success';
    const horaIngreso = data.hora || '-';

    if (data.datos) {
      // Estudiante encontrado
      html = `
        <div class="message success">¡Bienvenido!</div>
        <div class="student-name">${data.datos.apellidos_nombres}</div>
        <div class="student-meta">${data.datos.escuela}</div>
        <div class="student-meta" style="font-size:0.9rem; margin-top:5px;">${data.datos.facultad}</div>
        <div class="details" style="margin-top:15px; font-size:0.9rem; color:#059669;">
          Hora: <b>${horaIngreso}</b> • Turno: ${data.turno}
        </div>
      `;
    } else {
      // Estudiante NO encontrado (pero registrado como visitante/no-data)
      html = `
        <div class="message success">Ingreso Registrado</div>
        <div class="details">Datos no encontrados en padrón.</div>
        <div class="details" style="margin-top:10px;">Hora: <b>${horaIngreso}</b></div>
      `;
    }

  } else {
    playSound('error');
    // Error / Bloqueo (Ya ingresó, código inválido, etc.)
    // Distinguir entre "Bloqueado por duplicado" (Warn) y "Error de sistema/código" (Err)
    if (data.bloqueado) {
      statusClass = 'status-warning';
      html = `
        <div class="message warning">YA SE REGISTRO</div>
        <div class="student-name">${data.mensaje}</div>
        <div class="details" style="margin-top:10px;">
           Hora anterior: <b>${data.hora || '--:--'}</b>
        </div>
      `;
    } else {
      statusClass = 'status-error';
      html = `
        <div class="message error">Error</div>
        <div class="details">${data.mensaje || 'Código no reconocido'}</div>
      `;
    }
  }

  // Actualizar DOM
  mainCard.className = `card ${statusClass}`;
  resultArea.innerHTML = html;

  // Programar reset
  resetTimer = setTimeout(resetUI, RESET_DELAY_MS);
}

// Renderizar error de red
function renderError(msg) {
  clearTimeout(resetTimer);
  mainCard.className = 'card status-error';
  resultArea.innerHTML = `
    <div class="message error">Error de Sistema</div>
    <div class="details">${msg}</div>
  `;
  resetTimer = setTimeout(resetUI, RESET_DELAY_MS);
}

// Resetear a estado inicial
function resetUI() {
  mainCard.className = 'card';
  resultArea.innerHTML = `<div id="placeholder-anim">${placeholderContent}</div>`;
  scanInput.value = '';
  scanInput.focus();
}

// --- Contador ---
async function fetchCounter() {
  try {
    const res = await fetch(API_CONTADOR);
    const data = await res.json();
    if (data.ok) {
      // Animación simple de número
      counterVal.textContent = data.total;
    }
  } catch (e) {
    if(counterVal) counterVal.textContent = '-';
  }
}

// --- Event Listeners ---

// Mantener foco siempre en el input (SOLO SI EL MODAL NO ESTA ACTIVO)
document.addEventListener('click', (e) => {
  if (modal.classList.contains('active')) return; // No robar foco si el modal esta abierto
  if(scanInput) scanInput.focus();
});

if (scanInput) {
    scanInput.addEventListener('blur', () => {
      if (modal.classList.contains('active')) return; // No re-enfocar si estamos en el modal
      setTimeout(() => {
        if (!modal.classList.contains('active')) scanInput.focus();
      }, 100);
    });

    // Detectar "Enter" del lector de código de barras
    scanInput.addEventListener('keydown', (e) => {
      if (modal.classList.contains('active')) return; // Ignorar scanner si modal abierto
      if (e.key === 'Enter') {
        e.preventDefault();
        const code = scanInput.value.trim();
        if (code.length > 0) {
          processCode(code);
          scanInput.value = ''; // Limpiar para siguiente lectura
        }
      }
    });

    // Inicialización
    resetUI();
    fetchCounter();
    setInterval(fetchCounter, REFRESH_COUNTER_MS);
}
