/**
 * Main Application Controller for CTT FISEI AI Sales Dashboard
 */
let currentLeads = [];
let activeLeadId = null;
let currentStatusFilter = 'TODOS';

document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupCRMTable();
  setupCoursesTab();
  setupCertificateValidator();
  setupConfigTab();
  setupLeadModal();
  initSimulator();

  // Load initial data
  loadDashboardData();

  // Periodic real-time poll every 12 seconds
  setInterval(loadDashboardData, 12000);
});

// Make refresh accessible globally for the simulator
window.refreshDashboardData = loadDashboardData;

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icon = type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation';
  toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Navigation between tabs
function setupNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const panes = document.querySelectorAll('.tab-pane');

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetId = item.getAttribute('data-tab');
      if (!targetId || targetId === 'tab-simulator') return; // Simulator handled separately

      navItems.forEach(n => n.classList.remove('active'));
      item.classList.add('active');

      panes.forEach(pane => {
        pane.style.display = (pane.id === targetId) ? 'block' : 'none';
      });

      // Update titles
      const titles = {
        'tab-dashboard': ['Panel de Control & Inteligencia Comercial', 'Monitoreo en tiempo real de prospectos y cierre de admisiones'],
        'tab-pipeline': ['Pipeline de Ventas y CRM', 'Gestión, calificación y seguimiento activo de prospectos'],
        'tab-courses': ['Catálogo de Cursos Tecnológicos', 'Programas académicos sincronizados con el sitio oficial CTT FISEI'],
        'tab-certificates': ['Verificación de Certificados', 'Validación de códigos QR y autenticidad académica institucional'],
        'tab-config': ['Configuración del Sistema', 'Parámetros del Bot de Telegram y Conexión de Modelos IA']
      };
      if (titles[targetId]) {
        document.getElementById('page-title').textContent = titles[targetId][0];
        document.getElementById('page-subtitle').textContent = titles[targetId][1];
      }

      if (targetId === 'tab-courses') loadCourses();
    });
  });
}

// Fetch metrics & leads
async function loadDashboardData() {
  try {
    const [metricsResp, leadsResp] = await Promise.all([
      fetch('/api/metrics'),
      fetch('/api/leads')
    ]);

    if (metricsResp.ok) {
      const metrics = await metricsResp.json();
      updateKPICards(metrics);
      if (window.initCharts) initCharts(metrics);
    }

    if (leadsResp.ok) {
      currentLeads = await leadsResp.json();
      renderHotLeads(currentLeads);
      renderCRMTable(currentLeads);
    }

    // Check system status
    fetchConfigStatus();

  } catch (err) {
    console.error('Error loading dashboard data:', err);
  }
}

function updateKPICards(metrics) {
  document.getElementById('kpi-total-leads').textContent = metrics.total_leads || 0;
  document.getElementById('kpi-hot-leads').textContent = metrics.hot_leads || 0;
  document.getElementById('kpi-closed-leads').textContent = metrics.closed_leads || 0;
  document.getElementById('kpi-total-messages').textContent = metrics.total_messages || 0;
  document.getElementById('kpi-conversion-rate').textContent = `${metrics.conversion_rate || 0}%`;

  const badge = document.getElementById('badge-hot-count');
  if (badge) {
    badge.textContent = metrics.hot_leads || 0;
    badge.style.display = (metrics.hot_leads > 0) ? 'inline-block' : 'none';
  }
}

// Hot Leads (A Punto de Inscribirse)
function renderHotLeads(leads) {
  const container = document.getElementById('hot-leads-container');
  if (!container) return;

  const hotLeads = leads.filter(l => l.status === 'A PUNTO DE INSCRIBIRSE');

  if (hotLeads.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 20px; text-align: center; color: var(--text-muted); font-size: 13px;">
        <i class="fa-solid fa-bell-slash" style="font-size: 24px; color: var(--text-dim); margin-bottom: 8px; display: block;"></i>
        Actualmente no hay prospectos en estado de cierre inmediato. Interactúa con el bot para ver alertas en vivo.
      </div>
    `;
    return;
  }

  container.innerHTML = hotLeads.map(lead => {
    const scorePct = Math.round((lead.intent_score || 0.8) * 100);
    const course = lead.course_title || 'Curso Tecnológico';
    const tgUsername = lead.username ? `@${lead.username}` : `ID: ${lead.telegram_id}`;
    const userTypeStr = formatUserType(lead.user_type);
    const phone = lead.phone ? lead.phone : 'No registrado';
    const waLink = lead.phone ? `https://wa.me/593${lead.phone.replace(/^0/, '')}?text=Hola%20${encodeURIComponent(lead.full_name)},%20te%20saludamos%20del%20CTT-FISEI%20UTA%20respecto%20a%20tu%20inscripción.` : '#';

    return `
      <div class="hot-lead-card">
        <div class="hot-lead-card-header">
          <div class="lead-user-info">
            <h4>${escapeHtml(lead.full_name || 'Prospecto Interesado')}</h4>
            <div class="lead-user-meta">
              <span><i class="fa-brands fa-telegram"></i> ${escapeHtml(tgUsername)}</span>
              <span>•</span>
              <span class="badge-user-type">${userTypeStr}</span>
            </div>
          </div>
          <div class="score-badge high">
            <i class="fa-solid fa-fire"></i> ${scorePct}%
          </div>
        </div>

        <div class="hot-course-target">
          <i class="fa-solid fa-graduation-cap"></i> ${escapeHtml(course)}
        </div>

        <div class="hot-message-bubble">
          "${escapeHtml(lead.last_message || 'Solicitó información de pago e inscripción.')}"
        </div>

        <div class="hot-card-actions">
          ${lead.username ? `
            <a href="https://t.me/${lead.username}" target="_blank" class="btn btn-secondary btn-sm" style="flex: 1; justify-content: center;" title="Abrir chat en Telegram">
              <i class="fa-brands fa-telegram" style="color: #38bdf8;"></i> Telegram
            </a>
          ` : ''}
          ${lead.phone ? `
            <a href="${waLink}" target="_blank" class="btn btn-secondary btn-sm" style="flex: 1; justify-content: center;" title="Contactar por WhatsApp">
              <i class="fa-brands fa-whatsapp" style="color: #4ade80;"></i> WhatsApp
            </a>
          ` : ''}
          <button class="btn btn-primary btn-sm btn-open-lead" data-id="${lead.id}" style="flex: 1; justify-content: center;">
            <i class="fa-solid fa-handshake"></i> Cerrar Venta
          </button>
        </div>
      </div>
    `;
  }).join('');

  // Attach modal openers
  container.querySelectorAll('.btn-open-lead').forEach(btn => {
    btn.addEventListener('click', () => {
      openLeadModal(parseInt(btn.getAttribute('data-id')));
    });
  });
}

// CRM Pipeline Table
function setupCRMTable() {
  const searchInput = document.getElementById('crm-search');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      renderCRMTable(currentLeads);
    });
  }

  const filterTabs = document.querySelectorAll('.filter-tab');
  filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      filterTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentStatusFilter = tab.getAttribute('data-status');
      renderCRMTable(currentLeads);
    });
  });
}

function renderCRMTable(leads) {
  const tbody = document.getElementById('crm-table-body');
  if (!tbody) return;

  const search = (document.getElementById('crm-search')?.value || '').toLowerCase();

  let filtered = leads;
  if (currentStatusFilter && currentStatusFilter !== 'TODOS') {
    filtered = filtered.filter(l => l.status === currentStatusFilter);
  }
  if (search) {
    filtered = filtered.filter(l => 
      (l.full_name || '').toLowerCase().includes(search) ||
      (l.username || '').toLowerCase().includes(search) ||
      (l.phone || '').includes(search) ||
      (l.course_title || '').toLowerCase().includes(search)
    );
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; padding: 30px; color: var(--text-dim);">
          No se encontraron prospectos con los filtros actuales.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = filtered.map(lead => {
    const scorePct = Math.round((lead.intent_score || 0.1) * 100);
    const scoreClass = scorePct >= 80 ? 'high' : (scorePct >= 50 ? 'mid' : 'low');
    const badgeStatusClass = getStatusBadgeClass(lead.status);
    const userTypeStr = formatUserType(lead.user_type);
    const timeAgo = formatTimeAgo(lead.last_interaction);

    return `
      <tr>
        <td>
          <div style="font-weight: 700; color: #fff;">${escapeHtml(lead.full_name || 'Prospecto')}</div>
          <div style="font-size: 11px; color: var(--text-dim);">
            <i class="fa-brands fa-telegram"></i> @${escapeHtml(lead.username || lead.telegram_id)}
            ${lead.phone ? ` • <i class="fa-solid fa-phone"></i> ${lead.phone}` : ''}
          </div>
        </td>
        <td><span class="badge-user-type">${userTypeStr}</span></td>
        <td style="max-width: 180px;">
          <div style="font-weight: 600; color: var(--accent-cyan); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(lead.course_title || 'No definido')}">
            ${escapeHtml(lead.course_title || 'General')}
          </div>
        </td>
        <td>
          <div class="intent-bar-container">
            <div class="intent-track">
              <div class="intent-fill ${scoreClass}" style="width: ${scorePct}%;"></div>
            </div>
            <span class="intent-percent">${scorePct}%</span>
          </div>
        </td>
        <td>
          <span class="badge ${badgeStatusClass}">${escapeHtml(lead.status)}</span>
        </td>
        <td>
          <span style="font-size: 11px; font-weight: 700; color: ${lead.closure_probability === 'ALTA' ? '#f87171' : (lead.closure_probability === 'MEDIA' ? '#38bdf8' : '#94a3b8')}">
            ${lead.closure_probability || 'MEDIA'}
          </span>
        </td>
        <td style="max-width: 220px; color: var(--text-muted); font-size: 12px;">
          <div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(lead.last_message || '')}">
            "${escapeHtml(lead.last_message || 'Sin mensajes')}"
          </div>
          <small style="font-size: 10px; color: var(--text-dim);">${timeAgo}</small>
        </td>
        <td>
          <button class="btn btn-secondary btn-sm btn-open-crm-lead" data-id="${lead.id}">
            <i class="fa-solid fa-eye"></i> Gestionar
          </button>
        </td>
      </tr>
    `;
  }).join('');

  tbody.querySelectorAll('.btn-open-crm-lead').forEach(btn => {
    btn.addEventListener('click', () => {
      openLeadModal(parseInt(btn.getAttribute('data-id')));
    });
  });
}

function getStatusBadgeClass(status) {
  switch (status) {
    case 'A PUNTO DE INSCRIBIRSE': return 'badge-hot';
    case 'INTERESADO': return 'badge-interested';
    case 'INSCRITO': return 'badge-closed';
    case 'SEGUIMIENTO_PENDIENTE': return 'badge-pending';
    default: return 'badge-new';
  }
}

function formatUserType(type) {
  switch (type) {
    case 'ESTUDIANTE_UTA': return '🎓 Estudiante UTA';
    case 'DOCENTE_GRADUADO_UTA': return '🏛️ Graduado UTA';
    case 'PUBLICO_GENERAL': return '🌐 Público General';
    default: return '👤 No Definido';
  }
}

function formatTimeAgo(isoDate) {
  if (!isoDate) return '';
  const diff = (new Date() - new Date(isoDate)) / 1000;
  if (diff < 60) return 'Hace un momento';
  if (diff < 3600) return `Hace ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `Hace ${Math.floor(diff / 3600)} h`;
  return `Hace ${Math.floor(diff / 86400)} d`;
}

// Courses Tab
function setupCoursesTab() {
  const syncBtn = document.getElementById('btn-sync-catalog');
  const syncTopBtn = document.getElementById('btn-sync-courses');

  const handleSync = async () => {
    showToast('Iniciando sincronización con CTT FISEI...', 'success');
    try {
      const resp = await fetch('/api/courses/scrape', { method: 'POST' });
      const data = await resp.json();
      showToast(data.message || 'Sincronización en curso', 'success');
      setTimeout(loadCourses, 2000);
    } catch (e) {
      showToast('Error al conectar con el scraper', 'error');
    }
  };

  if (syncBtn) syncBtn.addEventListener('click', handleSync);
  if (syncTopBtn) syncTopBtn.addEventListener('click', handleSync);
}

async function loadCourses() {
  const container = document.getElementById('courses-grid-container');
  if (!container) return;

  try {
    const resp = await fetch('/api/courses');
    if (!resp.ok) return;
    const courses = await resp.json();

    container.innerHTML = courses.map(c => {
      const statusBadge = c.status === 'ABIERTO' 
        ? '<span class="badge badge-closed"><i class="fa-solid fa-door-open"></i> Abierto</span>'
        : '<span class="badge badge-new">Cerrado</span>';

      return `
        <div class="course-card">
          <div>
            <div class="course-header-badge">
              <span class="course-category-tag">${escapeHtml(c.category || 'Tecnología')}</span>
              ${statusBadge}
            </div>
            <h3 class="course-title" style="margin-top: 8px;">${escapeHtml(c.title)}</h3>
            <p style="font-size: 12px; color: var(--text-muted); margin-top: 6px; line-height: 1.4;">
              ${escapeHtml((c.description || '').substring(0, 140))}...
            </p>
          </div>

          <div style="display: flex; flex-direction: column; gap: 10px;">
            <div class="course-meta-row">
              <span><i class="fa-solid fa-clock"></i> ${c.hours} Horas</span>
              <span>•</span>
              <span><i class="fa-solid fa-laptop"></i> ${escapeHtml(c.modality || 'Virtual')}</span>
              <span>•</span>
              <span><i class="fa-solid fa-fire"></i> ${c.inquiries_count || 0} consultas</span>
            </div>

            <div class="price-comparison-box">
              <div class="price-item uta">
                <small>Estudiante UTA</small>
                <span>$${(c.price_uta_student || 40).toFixed(2)}</span>
              </div>
              <div class="price-item">
                <small>Graduado UTA</small>
                <span>$${(c.price_uta_staff || 50).toFixed(2)}</span>
              </div>
              <div class="price-item">
                <small>Público General</small>
                <span>$${(c.price_general || 60).toFixed(2)}</span>
              </div>
            </div>

            <div style="display: flex; gap: 8px; margin-top: 4px;">
              <a href="${c.registration_url || 'https://ctt-talleresfisei.uta.edu.ec/course.php'}" target="_blank" class="btn btn-primary btn-sm" style="flex: 1; justify-content: center;">
                <i class="fa-solid fa-file-pen"></i> Formulario UTA
              </a>
              <button class="btn btn-secondary btn-sm btn-simulate-course" data-title="${escapeHtml(c.title)}">
                <i class="fa-solid fa-robot"></i> Probar en Bot
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    container.querySelectorAll('.btn-simulate-course').forEach(btn => {
      btn.addEventListener('click', () => {
        const title = btn.getAttribute('data-title');
        const input = document.getElementById('sim-input');
        if (input) input.value = `Quiero información sobre ${title}`;
        document.getElementById('sim-drawer')?.classList.add('open');
      });
    });

  } catch (err) {
    console.error('Error loading courses:', err);
  }
}

// Certificate Validator Tab
function setupCertificateValidator() {
  const searchInput = document.getElementById('cert-search-input');
  const btnSearch = document.getElementById('btn-search-cert');
  const resultBox = document.getElementById('cert-result-box');

  const doSearch = async () => {
    const q = searchInput.value.trim();
    if (!q) {
      showToast('Ingresa un código o número de cédula', 'error');
      return;
    }

    try {
      const resp = await fetch(`/api/certificates/verify?query=${encodeURIComponent(q)}`);
      const data = await resp.json();

      resultBox.style.display = 'block';

      if (data.found && data.certificate) {
        const cert = data.certificate;
        resultBox.innerHTML = `
          <div class="cert-card-preview">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span class="badge badge-closed"><i class="fa-solid fa-circle-check"></i> Certificado Válido y Oficial</span>
              <span style="font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #6ee7b7;">${escapeHtml(cert.cert_code)}</span>
            </div>

            <div>
              <h3 style="font-size: 18px; color: #fff;">${escapeHtml(cert.student_name)}</h3>
              <p style="font-size: 12px; color: var(--text-dim);">Cédula / Identificación: ${escapeHtml(cert.student_cedula || 'Registrada')}</p>
            </div>

            <div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: var(--radius-sm);">
              <div style="font-size: 11px; color: var(--text-dim); text-transform: uppercase;">Programa Aprobado</div>
              <h4 style="font-size: 15px; color: var(--accent-cyan); margin-top: 2px;">${escapeHtml(cert.course_name)}</h4>
              <div style="display: flex; gap: 14px; margin-top: 8px; font-size: 12px; color: var(--text-muted);">
                <span><i class="fa-solid fa-clock"></i> ${cert.hours} Horas Académicas</span>
                <span>•</span>
                <span><i class="fa-solid fa-star"></i> Nota: ${cert.grade}/10.0</span>
                <span>•</span>
                <span><i class="fa-solid fa-calendar"></i> ${cert.issue_date}</span>
              </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
              <small style="color: var(--text-dim); font-size: 11px;">Avalado por el CTT FISEI - Universidad Técnica de Ambato</small>
              <a href="${cert.qr_verification_url || '#'}" target="_blank" class="btn btn-secondary btn-sm">
                <i class="fa-solid fa-qrcode"></i> Validar en Portal Oficial
              </a>
            </div>
          </div>
        `;
      } else {
        resultBox.innerHTML = `
          <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: var(--radius-md); padding: 20px; text-align: left;">
            <h4 style="color: #fca5a5; font-size: 14px; margin-bottom: 6px;"><i class="fa-solid fa-triangle-exclamation"></i> No se encontró registro inmediato</h4>
            <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">${data.message}</p>
            <a href="${data.official_url}" target="_blank" class="btn btn-primary btn-sm">
              <i class="fa-solid fa-arrow-up-right-from-square"></i> Abrir Portal de Validación CTT
            </a>
          </div>
        `;
      }

    } catch (e) {
      showToast('Error al verificar certificado', 'error');
    }
  };

  if (btnSearch) btnSearch.addEventListener('click', doSearch);
  if (searchInput) {
    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') doSearch();
    });
  }
}

// Config Tab
function setupConfigTab() {
  const btnSaveToken = document.getElementById('btn-save-token');
  const btnSaveGemini = document.getElementById('btn-save-gemini');

  if (btnSaveToken) {
    btnSaveToken.addEventListener('click', async () => {
      const token = document.getElementById('input-tg-token').value.trim();
      if (!token) {
        showToast('Ingresa un token de bot válido', 'error');
        return;
      }
      try {
        const resp = await fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ telegram_bot_token: token })
        });
        const data = await resp.json();
        showToast(data.message, data.success ? 'success' : 'error');
        fetchConfigStatus();
      } catch (e) {
        showToast('Error al guardar token', 'error');
      }
    });
  }

  if (btnSaveGemini) {
    btnSaveGemini.addEventListener('click', async () => {
      const key = document.getElementById('input-gemini-key').value.trim();
      try {
        const resp = await fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ gemini_api_key: key })
        });
        const data = await resp.json();
        showToast(data.message, 'success');
        fetchConfigStatus();
      } catch (e) {
        showToast('Error al guardar Gemini Key', 'error');
      }
    });
  }
}

async function fetchConfigStatus() {
  try {
    const resp = await fetch('/api/config');
    if (!resp.ok) return;
    const cfg = await resp.json();

    const indicator = document.getElementById('token-status-indicator');
    if (indicator) {
      if (cfg.telegram_bot_active) {
        indicator.innerHTML = `<span style="color: var(--accent-emerald);"><i class="fa-solid fa-circle-check"></i> Bot de Telegram Activo y Polling</span> (${cfg.telegram_bot_token_status})`;
      } else {
        indicator.innerHTML = `<span style="color: var(--text-dim);"><i class="fa-solid fa-circle-xmark"></i> Bot de Telegram Inactivo</span> (${cfg.telegram_bot_token_status})`;
      }
    }

    const botStatusText = document.getElementById('bot-status-text');
    if (botStatusText) {
      botStatusText.textContent = cfg.telegram_bot_active ? 'Telegram + Web Activo' : 'Simulador Web Activo';
    }
  } catch (e) {}
}

// Lead Detail Modal & Sales Closure
function setupLeadModal() {
  const modal = document.getElementById('lead-modal');
  const closeBtn = document.getElementById('btn-close-lead-modal');
  const btnSaveNotes = document.getElementById('btn-save-notes');
  const btnMarkEnrolled = document.getElementById('btn-mark-enrolled');

  if (closeBtn) closeBtn.addEventListener('click', () => modal.classList.remove('active'));
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.remove('active');
    });
  }

  if (btnSaveNotes) {
    btnSaveNotes.addEventListener('click', async () => {
      if (!activeLeadId) return;
      const notes = document.getElementById('modal-lead-notes').value;
      try {
        await fetch(`/api/leads/${activeLeadId}/notes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ notes })
        });
        showToast('Notas del prospecto guardadas con éxito', 'success');
        loadDashboardData();
      } catch (e) {
        showToast('Error al guardar notas', 'error');
      }
    });
  }

  if (btnMarkEnrolled) {
    btnMarkEnrolled.addEventListener('click', async () => {
      if (!activeLeadId) return;
      try {
        await fetch(`/api/leads/${activeLeadId}/status`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'INSCRITO', notes: 'Venta cerrada y matrícula confirmada por organizador.' })
        });
        showToast('🎉 ¡Venta cerrada! Prospecto marcado como INSCRITO', 'success');
        modal.classList.remove('active');
        loadDashboardData();
      } catch (e) {
        showToast('Error al cerrar venta', 'error');
      }
    });
  }
}

async function openLeadModal(leadId) {
  activeLeadId = leadId;
  const modal = document.getElementById('lead-modal');
  if (!modal) return;

  try {
    const resp = await fetch(`/api/leads/${leadId}`);
    if (!resp.ok) return;
    const data = await resp.json();
    const lead = data.lead;
    const conversations = data.conversations || [];

    document.getElementById('modal-lead-name').textContent = lead.full_name || 'Prospecto CTT';
    document.getElementById('modal-lead-course').textContent = lead.course_title || 'General';
    document.getElementById('modal-lead-type').innerHTML = `<span class="badge-user-type">${formatUserType(lead.user_type)}</span>`;
    document.getElementById('modal-lead-phone').textContent = lead.phone || 'No registrado aún';
    
    const scorePct = Math.round((lead.intent_score || 0.1) * 100);
    document.getElementById('modal-lead-score').innerHTML = `
      <div class="intent-bar-container">
        <div class="intent-track">
          <div class="intent-fill ${scorePct >= 80 ? 'high' : 'mid'}" style="width: ${scorePct}%;"></div>
        </div>
        <span class="intent-percent">${scorePct}%</span>
      </div>
    `;

    document.getElementById('modal-lead-notes').value = lead.notes || '';

    // Action links
    const btnTg = document.getElementById('btn-action-tg');
    if (lead.username) {
      btnTg.href = `https://t.me/${lead.username}`;
      btnTg.style.display = 'inline-flex';
    } else {
      btnTg.style.display = 'none';
    }

    const btnWa = document.getElementById('btn-action-wa');
    if (lead.phone) {
      btnWa.href = `https://wa.me/593${lead.phone.replace(/^0/, '')}?text=Hola%20${encodeURIComponent(lead.full_name)},%20te%20escribimos%20del%20CTT-FISEI%20UTA%20para%20confirmar%20tu%20inscripción.`;
      btnWa.style.display = 'inline-flex';
    } else {
      btnWa.style.display = 'none';
    }

    // Render transcript
    const transcriptBox = document.getElementById('modal-chat-transcript');
    if (conversations.length === 0) {
      transcriptBox.innerHTML = '<div style="color: var(--text-dim); text-align: center; padding: 20px;">Sin historial de conversación.</div>';
    } else {
      transcriptBox.innerHTML = conversations.map(c => `
        <div class="chat-bubble ${c.sender === 'user' ? 'user' : 'bot'}">
          <div>${escapeHtml(c.message)}</div>
          <div class="chat-meta">
            ${c.sender === 'user' ? 'Usuario' : 'Agente IA'} 
            ${c.detected_intent ? `• [${c.detected_intent}]` : ''} 
            • ${formatTimeAgo(c.timestamp)}
          </div>
        </div>
      `).join('');
      transcriptBox.scrollTop = transcriptBox.scrollHeight;
    }

    modal.classList.add('active');

  } catch (e) {
    console.error('Error opening lead detail:', e);
  }
}

function escapeHtml(string) {
  return String(string || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
