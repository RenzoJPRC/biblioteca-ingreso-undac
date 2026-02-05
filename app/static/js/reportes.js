// Inicializar fechas (Últimos 7 días)
const today = new Date();
const lastWeek = new Date();
lastWeek.setDate(today.getDate() - 6);

const endDateEl = document.getElementById('endDate');
const startDateEl = document.getElementById('startDate');

if (endDateEl) endDateEl.valueAsDate = today;
if (startDateEl) startDateEl.valueAsDate = lastWeek;

let chartTrendInst = null;
let chartFacInst = null;

async function loadData() {
    const start = document.getElementById('startDate').value;
    const end = document.getElementById('endDate').value;

    if (!start || !end) return alert("Seleccione fechas válidas");

    try {
        const res = await fetch(`/admin/api/stats?start=${start}&end=${end}`);
        const data = await res.json();

        if (!data.ok) return alert("Error cargando datos");

        // Update KPIs
        document.getElementById('kpiTotal').textContent = data.kpi.total;
        document.getElementById('kpiAvg').textContent = data.kpi.avg_daily;
        document.getElementById('kpiUnique').textContent = data.kpi.unique_students;
        document.getElementById('kpiTopDay').innerText = data.kpi.top_day_name || '-';

        // Update Trend Chart
        renderTrendChart(data.trend.labels, data.trend.values);

        // Update Faculty Chart
        renderFacultyChart(data.faculty.labels, data.faculty.values);

        // Update Table
        renderTable(data.top_schools);

    } catch (e) {
        console.error(e);
        alert("Error de conexión");
    }
}

function renderTrendChart(labels, values) {
    const ctx = document.getElementById('chartTrend');
    if (chartTrendInst) chartTrendInst.destroy();

    chartTrendInst = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Ingresos',
                data: values,
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true },
                x: { grid: { display: false } }
            }
        }
    });
}

function renderFacultyChart(labels, values) {
    const ctx = document.getElementById('chartFacultad');
    if (chartFacInst) chartFacInst.destroy();

    const colors = [
        '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
        '#8b5cf6', '#ec4899', '#6366f1', '#14b8a6'
    ];

    chartFacInst = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 10, padding: 15 } }
            }
        }
    });
}

function renderTable(rows) {
    const tbody = document.getElementById('tableSchoolsBody');
    tbody.innerHTML = '';

    rows.forEach((r, idx) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
<td>#${idx + 1}</td>
<td><b>${r.escuela}</b></td>
<td style="color:#6b7280;">${r.facultad}</td>
<td style="text-align:right;"><b>${r.total}</b></td>
`;
        tbody.appendChild(tr);
    });

    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:2rem;">Sin datos en este periodo</td></tr>';
    }
}

// Load initial
loadData();

// Auto Logout - 10 Minutos
(function () {
    let timeout;
    const LIMIT = 10 * 60 * 1000; // 10 min

    function resetTimer() {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            window.location.href = '/logout';
        }, LIMIT);
    }

    window.onload = resetTimer;
    document.onmousemove = resetTimer;
    document.onkeypress = resetTimer;
    document.onclick = resetTimer;
    document.onscroll = resetTimer;
})();
