/**
 * Charts module for CTT FISEI Dashboard - Light Mode Professional Theme
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
    if (t.length > 26) t = t.substring(0, 24) + '...';
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
          '#1b3252', // Navy (Image 1)
          '#9e2222', // Red (Image 1)
          '#1e3a61',
          '#b91c1c',
          '#0284c7',
          '#16a34a'
        ],
        borderWidth: 0,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          titleColor: '#ffffff',
          bodyColor: '#e2e8f0',
          borderColor: '#e2e8f0',
          borderWidth: 1,
          padding: 10,
          cornerRadius: 6
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#64748b', font: { size: 11, family: 'Poppins' } }
        },
        y: {
          grid: { color: '#f1f5f9' },
          ticks: { color: '#64748b', stepSize: 2 }
        }
      }
    }
  });
}

function renderFunnelChart(statusDist, userTypes) {
  const ctx = document.getElementById('chartFunnel');
  if (!ctx) return;

  const labels = ['Nuevos', 'Interesados', 'A Punto de Inscribirse', 'Inscritos'];
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
          '#94a3b8',
          '#1b3252',
          '#9e2222',
          '#16a34a'
        ],
        borderColor: '#ffffff',
        borderWidth: 3,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#334155',
            font: { size: 11, family: 'Poppins' },
            padding: 12,
            usePointStyle: true
          }
        },
        tooltip: {
          backgroundColor: '#0f172a',
          titleColor: '#ffffff',
          bodyColor: '#e2e8f0',
          padding: 10,
          cornerRadius: 6
        }
      },
      cutout: '65%'
    }
  });
}
