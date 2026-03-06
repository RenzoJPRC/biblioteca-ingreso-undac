// FUNCIONES JS AISLADAS DE ADMIN PERSONAL
let currentPage = 1;
let totalPages = 1;

function inicializarAdminPersonal() {
    buscarPersonal();

    const inputBusqueda = document.getElementById('input-busqueda');
    if (inputBusqueda) {
        inputBusqueda.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') nuevaBusqueda();
        });
    }

    const modalForm = document.getElementById('form-personal');
    if (modalForm) {
        // Remover cualquier submit inline previo, lo manejamos aquí
        modalForm.onsubmit = async function (e) {
            e.preventDefault();
            await submitGuardarPersonal(e);
        }
    }
}

function buscarPersonal(pagina = 1) {
    const inputQ = document.getElementById('input-busqueda');
    const q = inputQ ? inputQ.value : '';
    const btnSearch = document.getElementById('btn-search');

    if (btnSearch) btnSearch.disabled = true;

    fetch(`/admin/buscar_personal?q=${encodeURIComponent(q)}&page=${pagina}`)
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('tabla-body');
            if (!tbody) return;

            tbody.innerHTML = '';
            currentPage = data.pagination.page;
            totalPages = data.pagination.total_pages;

            if (data.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="px-6 py-8 text-center text-slate-400"><i class="ph ph-empty text-3xl mb-2 block"></i>No hay personal encontrado</td></tr>`;
            } else {
                data.data.forEach(p => {
                    let row = `
                        <tr class="hover:bg-slate-50 transition-colors group">
                            <td class="px-6 py-3 font-mono text-slate-500">${p.dni}</td>
                            <td class="px-6 py-3 font-bold text-slate-700">${p.nombre}</td>
                            <td class="px-6 py-3 text-slate-600">${p.oficina}</td>
                            <td class="px-6 py-3">
                                <div class="flex flex-col gap-0.5 text-[11px] text-slate-500">
                                    ${p.correo_inst ? `<span class="flex items-center gap-1"><i class="ph ph-envelope-simple text-sky-500"></i> ${p.correo_inst}</span>` : ''}
                                    ${p.telefono ? `<span class="flex items-center gap-1"><i class="ph ph-phone text-emerald-500"></i> ${p.telefono}</span>` : ''}
                                </div>
                            </td>
                            <td class="px-6 py-3 text-right">
                                <div class="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button onclick='editarPersonal(${JSON.stringify(p).replace(/'/g, "&#39;")})'
                                        class="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Editar">
                                        <i class="ph ph-pencil-simple text-lg"></i>
                                    </button>
                                    <button onclick="eliminarPersonal(${p.id}, '${p.nombre}')"
                                        class="p-2 text-rose-600 hover:bg-rose-50 rounded-lg transition-colors" title="Eliminar">
                                        <i class="ph ph-trash text-lg"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;
                    tbody.innerHTML += row;
                });
            }
            actualizarControlesPaginacion();
        })
        .catch(err => {
            if (typeof showToast !== 'undefined') showToast("Error cargando personal", "error");
        })
        .finally(() => {
            if (btnSearch) btnSearch.disabled = false;
        });
}

function actualizarControlesPaginacion() {
    const btnPrev = document.getElementById('btn-prev');
    const btnNext = document.getElementById('btn-next');
    const select = document.getElementById('select-pagina');

    if (!btnPrev || !btnNext || !select) return;

    btnPrev.disabled = currentPage <= 1;
    btnNext.disabled = currentPage >= totalPages;

    select.innerHTML = '';
    let startPage = Math.max(1, currentPage - 10);
    let endPage = Math.min(totalPages, currentPage + 10);

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

function irAPagina(pagina) {
    buscarPersonal(parseInt(pagina));
}

function cambiarPagina(delta) {
    const nuevaPagina = currentPage + delta;
    if (nuevaPagina >= 1 && nuevaPagina <= Math.max(1, totalPages)) {
        buscarPersonal(nuevaPagina);
    }
}

function nuevaBusqueda() {
    buscarPersonal(1);
}

// --- MODALES Y CRUD ---

function abrirModalNuevo() {
    document.getElementById('form-personal').reset();
    document.getElementById('modal-id').value = '';
    document.getElementById('modal-titulo').innerHTML = '<i class="ph ph-briefcase text-purple-600 text-2xl"></i><span>Nuevo Personal Administrativo</span>';
    document.getElementById('modal-personal').classList.remove('hidden');
}

function cerrarModal() {
    document.getElementById('modal-personal').classList.add('hidden');
}

function editarPersonal(p) {
    document.getElementById('form-personal').reset();
    document.getElementById('modal-id').value = p.id;
    document.getElementById('modal-dni').value = p.dni;
    document.getElementById('modal-nombre').value = p.nombre;
    document.getElementById('modal-oficina').value = p.oficina;
    document.getElementById('modal-correo').value = p.correo_personal;
    document.getElementById('modal-correo-inst').value = p.correo_inst;
    document.getElementById('modal-telefono').value = p.telefono;

    document.getElementById('modal-titulo').innerHTML = '<i class="ph ph-pencil-simple text-purple-600 text-2xl"></i><span>Editar Personal</span>';
    document.getElementById('modal-personal').classList.remove('hidden');
}

async function submitGuardarPersonal(e) {
    const data = {
        id: document.getElementById('modal-id').value,
        dni: document.getElementById('modal-dni').value,
        nombre: document.getElementById('modal-nombre').value,
        oficina: document.getElementById('modal-oficina').value,
        correo_personal: document.getElementById('modal-correo').value,
        correo_inst: document.getElementById('modal-correo-inst').value,
        telefono: document.getElementById('modal-telefono').value
    };

    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="ph ph-spinner animate-spin"></i> Guardando...';

    try {
        const res = await fetch('/admin/guardar_personal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const resultJSON = await res.json();

        if (resultJSON.status === 'success') {
            cerrarModal();
            if (typeof showToast !== 'undefined') showToast("Personal guardado exitosamente", "success");
            buscarPersonal(currentPage);
        } else {
            if (typeof showToast !== 'undefined') showToast(resultJSON.msg, "error");
        }
    } catch (err) {
        console.error(err);
        if (typeof showToast !== 'undefined') showToast("Error de conexión.", "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="ph ph-floppy-disk mr-1"></i> Guardar Personal';
    }
}

function eliminarPersonal(id, nombre) {
    if (confirm(`¿Estás seguro de eliminar permanentemente a ${nombre}? Esto borrará todos sus historiales de ingreso también.`)) {
        fetch(`/admin/eliminar_personal/${id}`, { method: 'DELETE' })
            .then(res => res.json())
            .then(res => {
                if (res.status === 'success') {
                    if (typeof showToast !== 'undefined') showToast("Personal eliminado", "success");
                    buscarPersonal(1);
                } else {
                    if (typeof showToast !== 'undefined') showToast(res.msg, "error");
                }
            });
    }
}
