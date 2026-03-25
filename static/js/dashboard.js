// FUNCIONES JS AISLADAS DE ADMIN DASHBOARD
function inicializarGraficos(labelsHoras, dataHoras, labelsOrigenes, dataOrigenes) {
    // GRÁFICO HORAS
    const ctxHoras = document.getElementById('chartHoras');
    if (ctxHoras) {
        new Chart(ctxHoras, {
            type: 'line',
            data: {
                labels: labelsHoras,
                datasets: [{
                    label: 'Ingresos',
                    data: dataHoras,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        });
    }

    // GRÁFICO ORÍGENES
    const ctxEscuelas = document.getElementById('chartEscuelas');
    if (ctxEscuelas) {
        new Chart(ctxEscuelas, {
            type: 'doughnut',
            data: {
                labels: labelsOrigenes,
                datasets: [{
                    label: 'Cantidad',
                    data: dataOrigenes,
                    backgroundColor: ['#f97316', '#3b82f6', '#10b981', '#8b5cf6', '#f43f5e', '#14b8a6', '#eab308'],
                    hoverOffset: 4,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'right',
                        labels: { boxWidth: 12, padding: 15, font: { size: 11 } }
                    }
                },
                cutout: '65%',
                layout: { padding: 10 }
            }
        });
    }
}

function inicializarFormularioRangoFechas() {
    const formFechas = document.getElementById('form-fechas');
    if (formFechas) {
        formFechas.addEventListener('submit', function (e) {
            e.preventDefault();
            const ini = document.getElementById('fecha-inicio').value;
            const fin = document.getElementById('fecha-fin').value;
            if (ini && fin) {
                window.location.href = `/admin/exportar_ingresos_csv?inicio=${ini}&fin=${fin}`;
                document.getElementById('modal-fechas').classList.add('hidden');
            } else {
                if (typeof showToast !== 'undefined') {
                    showToast("Selecciona ambas fechas.", "error");
                } else {
                    alert("Selecciona ambas fechas.");
                }
            }
        });
    }
}

function inicializarAutoRefresh(isToday) {
    if (isToday === 'true') {
        setInterval(async function () {
            try {
                const res = await fetch('/admin/api/dashboard_data');
                const data = await res.json();

                // 1. Actualizar Tarjeta Principal
                document.querySelector('.text-3xl.font-bold.text-slate-800').innerText = data.total_hoy;

                // Actualizar badges
                const badges = document.querySelectorAll('.rounded-full.inline-block');
                if (badges.length >= 4) {
                    badges[0].innerText = `${data.total_alumnos} Alumnos`;
                    badges[1].innerText = `${data.total_egresados} Egresados`;
                    badges[2].innerText = `${data.total_visitantes} Externos`;
                    badges[3].innerText = `${data.total_personal} Trabajadores`;
                }

                // 2. Actualizar Tarjetas de Pisos
                const pisosHeaders = document.querySelectorAll('.text-2xl.font-bold.text-slate-700');
                if (pisosHeaders.length >= 3) {
                    pisosHeaders[0].innerText = data.pisos['1'] || 0;
                    pisosHeaders[1].innerText = data.pisos['2'] || 0;
                    pisosHeaders[2].innerText = data.pisos['3'] || 0;
                }

                // 3. Actualizar Tabla
                const tbody = document.getElementById('tbody-ultimos');
                if (tbody) {
                    tbody.innerHTML = '';
                    data.ultimos.forEach(reg => {
                        let pillHTML = '';
                        if (reg.tipo === 'Visitante') {
                            pillHTML = '<span class="text-[10px] bg-orange-100 text-orange-700 px-1 rounded ml-1">EXT</span>';
                        } else if (reg.tipo === 'Administrativo') {
                            pillHTML = '<span class="text-[10px] bg-purple-100 text-purple-700 px-1 rounded ml-1">ADM</span>';
                        }

                        let sedeStr = reg.sede || 'Central';
                        let ubicacionHTML = '';
                        if (sedeStr === 'Central') {
                            ubicacionHTML = `Piso ${reg.piso}`;
                        } else {
                            ubicacionHTML = `<span class="text-[10px] bg-emerald-100 text-emerald-700 font-bold px-2 py-1 rounded truncate inline-block max-w-[100px] uppercase">${sedeStr}</span>`;
                        }

                        const rowHTML = `
                            <tr data-sede="${sedeStr}">
                                <td class="px-6 py-3 text-slate-500">
                                    <span class="block text-xs font-bold text-slate-400 mb-0.5">${reg.fecha}</span>
                                    <span class="font-mono text-[13px]">${reg.hora}</span>
                                </td>
                                <td class="px-6 py-3 font-medium">
                                    ${reg.nombre} ${pillHTML}
                                </td>
                                <td class="px-6 py-3 text-slate-500">${reg.origen}</td>
                                <td class="px-6 py-3 text-center font-medium text-slate-600">${ubicacionHTML}</td>
                            </tr>
                        `;
                        tbody.innerHTML += rowHTML;
                    });

                    // Re-aplicar filtro actual
                    if (window.currentFiltroSede) {
                        filtrarUltimos(window.currentFiltroSede, null, true);
                    }
                }
            } catch (error) {
                console.log("Error consultando datos en vivo:", error);
            }
        }, 15000);
    }
}

function filtrarUltimos(categoria, btnElement = null, isAutoRefresh = false) {
    window.currentFiltroSede = categoria;

    // Actualizar estilos de botones si fue click manual
    if (!isAutoRefresh && btnElement) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('bg-slate-800', 'text-white');
            btn.classList.add('text-slate-500', 'hover:bg-slate-100');
        });
        btnElement.classList.remove('text-slate-500', 'hover:bg-slate-100');
        btnElement.classList.add('bg-slate-800', 'text-white');
    }

    // Filtrar filas
    const filas = document.querySelectorAll('#tbody-ultimos tr');
    filas.forEach(fila => {
        const sedeFila = fila.getAttribute('data-sede');
        if (categoria === 'Todos') {
            fila.style.display = '';
        } else if (categoria === 'Central') {
            fila.style.display = sedeFila === 'Central' ? '' : 'none';
        } else if (categoria === 'Filiales') {
            fila.style.display = sedeFila !== 'Central' ? '' : 'none';
        }
    });
}
