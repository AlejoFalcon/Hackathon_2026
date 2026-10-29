/**
 * Charts module for CTT FISEI Dashboard using Chart.js
 */
let coursesChartInstance = null;
let funnelChartInstance = null;

function initCharts(metrics) {
  renderCoursesChart(metrics.top_courses || []);
  renderFunnelChart(metrics.status_distribution || {}, metrics.user_types || {});
}

function renderCoursesChart(topCourses) {
  const ctx = document.getElementById('chartCourses');
  if (!ctx) return;

  const labels = topCourses.map(c => {
    let t = c.title;
    if (t.length > 28) t = t.substring(0, 26) + '...';
    return t;
  });
  const data = topCourses.map(c => c.inquiries_count + (c.interested_count || 0));

  if (coursesChartInstance) {
    coursesChartInstance.destroy();
  }

  coursesChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels.length ? labels : ['GH-600 Agentic AI', 'CCNA Redes', 'Python 1 & 2', 'Linux Essentials', 'Arduino'],
      datasets: [{
        label: 'Consultas e Interés',
        data: data.length ? data : [18, 14, 11, 8, 7],
        backgroundColor: [
          'rgba(239, 68, 68, 0.75)',
          'rgba(6, 182, 212, 0.75)',
          'rgba(99, 102, 241, 0.75)',
          'rgba(16, 185, 129, 0.75)',
          'rgba(245, 158, 11, 0.75)',
          'rgba(168, 85, 247, 0.75)'
        ],
        borderColor: [
          '#ef4444',
          '#06b6d4',
          '#6366f1',
          '#10b981',
          '#f59e0b',
          '#a855f7'
        ],
        borderWidth: 1.5,
        borderRadius: 8,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#131b2e',
          titleColor: '#fff',
          bodyColor: '#cbd5e1',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          padding: 10,
          cornerRadius: 8
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#94a3b8', font: { size: 11 } }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#94a3b8', stepSize: 2 }
        }
      }
    }
  });
}

function renderFunnelChart(statusDist, userTypes) {
  const ctx = document.getElementById('chartFunnel');
  if (!ctx) return;

  const labels = ['Nuevos', 'Interesados', '🔥 A Punto de Inscribirse', '✅ Inscritos'];
  const data = [
    statusDist['NUEVO'] || 1,
    statusDist['INTERESADO'] || 2,
    statusDist['A PUNTO DE INSCRIBIRSE'] || 2,
    statusDist['INSCRITO'] || 1
  ];

  if (funnelChartInstance) {
    funnelChartInstance.destroy();
  }

  funnelChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: [
          'rgba(148, 163, 184, 0.75)',
          'rgba(6, 182, 212, 0.75)',
          'rgba(239, 68, 68, 0.85)',
          'rgba(16, 185, 129, 0.85)'
        ],
        borderColor: '#0f1523',
        borderWidth: 3,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#cbd5e1',
            font: { size: 12 },
            padding: 14,
            usePointStyle: true
          }
        },
        tooltip: {
          backgroundColor: '#131b2e',
          titleColor: '#fff',
          bodyColor: '#cbd5e1',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          padding: 10,
          cornerRadius: 8
        }
      },
      cutout: '68%'
    }
  });
}
