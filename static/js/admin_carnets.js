let currentPage = 1;
let totalPages = 1;
let selectedIds = new Set(); // Almacena IDs seleccionados globalmente

// --- INICIALIZACIÓN ---
window.onload = function () {
    buscarAlumno();

    // Auto-update silencioso cada 15s
    setInterval(() => {
        if (!document.getElementById('modal-editar').classList.contains('hidden')) return;
        buscarAlumno(currentPage, true);
    }, 15000);
};

// --- BÚSQUEDA Y RENDERIZADO ---
function buscarAlumno(pagina = 1, silent = false) {
    const query = document.getElementById('input-busqueda').value;
    currentPage = pagina;

    const url = `/admin/buscar_alumno?q=${query}&page=${currentPage}`;

    // NO reseteamos selectedIds aquí para mantener selección entre búsquedas/páginas
    // Solo reseteamos el check "master" visual
    document.getElementById('check-todos').checked = false;

    // Indicador de carga
    const info = document.getElementById('info-paginacion');
    if (!silent) info.innerText = "Cargando...";

    fetch(url)
        .then(res => res.json())
        .then(resp => {
            const tbody = document.getElementById('tabla-body');

            const data = resp.data;
            const meta = resp.pagination;

            // Actualizar variables
            currentPage = meta.page;
            totalPages = meta.total_pages;

            if (meta.total_items === 0) {
                info.innerText = "0 Resultados";
                tbody.innerHTML = '<tr><td colspan="7" class="px-6 py-12 text-center text-slate-400 font-medium">No se encontraron alumnos</td></tr>';
                actualizarControlesPaginacion();
                actualizarContador(); // Actualizar barra con el total global
                return;
            }

            info.innerText = `Mostrando ${data.length} de ${meta.total_items} alumnos`;

            let html = "";
            data.forEach(alumno => {
                const isActivo = alumno.estado === 'ACTIVO';
                const estadoHtml = isActivo
                    ? `<span class="bg-emerald-100 text-emerald-700 px-2 py-1 rounded text-xs font-bold">ACTIVO</span>`
                    : `<span class="bg-rose-100 text-rose-700 px-2 py-1 rounded text-xs font-bold">VENCIDO</span>`;

                const fechaManual = alumno.fecha_manual
                    ? alumno.fecha_manual
                    : '<span class="text-slate-400 italic">Auto</span>';

                // Verificar si está seleccionado
                const isChecked = selectedIds.has(String(alumno.id)) ? 'checked' : '';

                html += `
                    <tr class="hover:bg-slate-50 transition-colors group">
                    <td class="px-6 py-3 text-center border-b border-slate-50 relative">
                        <input type="checkbox" value="${alumno.id}" onchange="toggleIndividual(this)" ${isChecked}
                               class="check-alumno w-4 h-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500 cursor-pointer">
                    </td>
                    <td class="px-6 py-3 font-medium text-slate-700 border-b border-slate-50">${alumno.nombre}</td>
                    <td class="px-6 py-3 border-b border-slate-50">
                        <div class="text-slate-600">${alumno.dni}</div>
                        <div class="text-xs text-slate-400 font-mono">${alumno.codigo}</div>
                    </td>
                    <td class="px-6 py-3 text-slate-500 text-xs border-b border-slate-50">${alumno.escuela}</td>
                    <td class="px-6 py-3 font-mono text-xs border-b border-slate-50">${fechaManual}</td>
                    <td class="px-6 py-3 border-b border-slate-50">${estadoHtml}</td>
                    <td class="px-6 py-3 text-center border-b border-slate-50">
                        <button onclick="abrirModal(${alumno.id}, '${alumno.nombre}', '${alumno.fecha_manual || ''}')" 
                                class="text-slate-400 hover:text-blue-600 p-2 rounded-full hover:bg-blue-50 transition-all" title="Editar Vencimiento">
                            <i class="ph ph-pencil-simple text-lg"></i>
                        </button>
                    </td>
                </tr>`;
            });

            tbody.innerHTML = html;

            actualizarControlesPaginacion();
            actualizarContador(); // Actualizar barra con el total global
        })
        .catch(err => console.error("Error cargando alumnos:", err));
}

// --- PAGINACIÓN UI ---
function actualizarControlesPaginacion() {
    const btnPrev = document.getElementById('btn-prev');
    const btnNext = document.getElementById('btn-next');
    const select = document.getElementById('select-pagina');

    btnPrev.disabled = currentPage <= 1;
    btnNext.disabled = currentPage >= totalPages;

    // Llenar select de paginas
    select.innerHTML = '';
    /* Optimización: Si son muchas páginas, no renderizar todas en el select, 
       pero por UX simple renderizaremos hasta 100 max o rango cercano */

    let startPage = Math.max(1, currentPage - 10);
    let endPage = Math.min(totalPages, currentPage + 10);

    // Siempre incluir la 1 y la ultima si estan lejos? 
    // Por simplicidad, mostramos un rango dinámico

    if (totalPages <= 20) {
        startPage = 1; endPage = totalPages;
    }

    for (let i = startPage; i <= endPage; i++) {
        const opt = document.createElement('option');
        opt.value = i;
        opt.innerText = i;
        if (i === currentPage) opt.selected = true;
        select.appendChild(opt);
    }
}

function cambiarPagina(delta) {
    const nuevaPagina = currentPage + delta;
    if (nuevaPagina >= 1 && nuevaPagina <= totalPages) {
        buscarAlumno(nuevaPagina);
    }
}

function irAPagina(pagina) {
    buscarAlumno(parseInt(pagina));
}

// Wrapper para el botón de buscar (resetea a pagina 1)
function nuevaBusqueda() {
    buscarAlumno(1);
}

// --- GESTIÓN DE SELECCIÓN (Checkboxes) ---

function toggleIndividual(checkbox) {
    const id = checkbox.value;
    if (checkbox.checked) {
        selectedIds.add(id);
    } else {
        selectedIds.delete(id);
        document.getElementById('check-todos').checked = false; // Desmarcar master si uno se desmarca
    }
    actualizarContador();
}

function toggleTodos() {
    const master = document.getElementById('check-todos');
    const checks = document.querySelectorAll('.check-alumno'); // Solo los visibles

    checks.forEach(c => {
        c.checked = master.checked;
        const id = c.value;
        if (master.checked) {
            selectedIds.add(id);
        } else {
            selectedIds.delete(id);
        }
    });
    actualizarContador();
}

function actualizarContador() {
    const totalSeleccionados = selectedIds.size;
    const barra = document.getElementById('barra-acciones');
    const contador = document.getElementById('contador-seleccionados');

    contador.innerText = totalSeleccionados;

    if (totalSeleccionados > 0) barra.classList.remove('hidden');
    else barra.classList.add('hidden');
}

// --- ACCIONES MASIVAS ---

function accionMasiva(accion) {
    const ids = Array.from(selectedIds);

    if (ids.length === 0) return;
    if (!confirm(`¿Estás seguro de aplicar esta acción a ${ids.length} alumnos seleccionados?`)) return;

    fetch('/admin/actualizar_carnet_masivo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: ids, accion: accion })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                alert(data.msg);
                selectedIds.clear(); // Limpiar selección tras acción exitosa
                actualizarContador();
                buscarAlumno(currentPage); // Recargar página actual
            } else {
                alert('Error: ' + data.msg);
            }
        });
}

// --- ACCIONES GLOBALES (Toda la Base de Datos) ---
function accionGlobal(accion) {
    const accionTexto = accion === 'activar' ? 'ACTIVAR' : 'DESACTIVAR';

    if (!confirm(`⚠️ ATENCIÓN: Estás a punto de ${accionTexto} a TODOS los alumnos registrados en la base de datos.\n\nEsta alteración aplicará globalmente ignorando las páginas actuales.\n\n¿Estás completamente seguro de continuar?`)) return;

    // Opcional: mostrar un indicador visual de que la operación global está en marcha
    const info = document.getElementById('info-paginacion');
    info.innerText = "Procesando operación masiva en la BD...";

    fetch('/admin/actualizar_carnet_global', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accion: accion })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                alert(data.msg);
                selectedIds.clear(); // Limpiar selecciones activas
                document.getElementById('check-todos').checked = false;
                actualizarContador();
                buscarAlumno(currentPage); // Recargar la vista para ver los cambios
            } else {
                alert('Error: ' + data.msg);
                info.innerText = "Error en la operación global";
            }
        })
        .catch(err => {
            console.error("Error en accion global:", err);
            alert("Ocurrió un error de red o de servidor.");
            info.innerText = "Error local";
        });
}

// --- MODAL DE EDICIÓN ---
function abrirModal(id, nombre, fecha) {
    document.getElementById('modal-alumno-id').value = id;
    document.getElementById('modal-nombre-alumno').innerText = nombre;
    document.getElementById('modal-fecha').value = fecha;
    document.getElementById('modal-editar').classList.remove('hidden');
}

function cerrarModal() {
    document.getElementById('modal-editar').classList.add('hidden');
}

function guardarFecha() {
    const id = document.getElementById('modal-alumno-id').value;
    const fecha = document.getElementById('modal-fecha').value;

    fetch('/admin/actualizar_carnet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id, fecha: fecha })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                cerrarModal();
                buscarAlumno(currentPage);
            } else {
                alert('Error: ' + data.msg);
            }
        });
}

// Buscador con Enter
document.getElementById('input-busqueda').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') nuevaBusqueda();
});
