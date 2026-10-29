/**
 * Simulator module for CTT FISEI Dashboard
 * Provides an interactive Telegram client right inside the web interface.
 */
function initSimulator() {
  const drawer = document.getElementById('sim-drawer');
  const btnToggle = document.getElementById('btn-toggle-sim');
  const navOpen = document.getElementById('nav-open-simulator');
  const btnClose = document.getElementById('btn-close-sim');
  const btnSend = document.getElementById('btn-sim-send');
  const input = document.getElementById('sim-input');
  const chatContainer = document.getElementById('sim-chat-container');
  const personaSelect = document.getElementById('sim-persona');

  function openDrawer() {
    drawer.classList.add('open');
  }

  function closeDrawer() {
    drawer.classList.remove('open');
  }

  if (btnToggle) btnToggle.addEventListener('click', openDrawer);
  if (navOpen) navOpen.addEventListener('click', openDrawer);
  if (btnClose) btnClose.addEventListener('click', closeDrawer);

  // Quick Action Buttons
  document.querySelectorAll('.sim-quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const query = btn.getAttribute('data-query');
      if (query) {
        input.value = query;
        sendMessage();
      }
    });
  });

  if (btnSend) btnSend.addEventListener('click', sendMessage);
  if (input) {
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') sendMessage();
    });
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    // Append user bubble
    appendMessage('user', text);
    input.value = '';

    // Selected Persona
    const personaVal = personaSelect.value;
    const [userType, userName] = personaVal.split('|');

    // Show typing indicator
    const typingId = showTypingIndicator();

    try {
      const resp = await fetch('/api/chat/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          user_id: userName.toLowerCase().replace(/[^a-z0-9]/g, '_'),
          user_name: userName,
          user_type: userType
        })
      });

      removeTypingIndicator(typingId);

      if (!resp.ok) {
        appendMessage('bot', '⚠️ Error al procesar tu solicitud con el agente.');
        return;
      }

      const data = await resp.json();
      appendBotResponse(data.bot_response, data.analysis);

      // Auto-refresh Dashboard metrics and leads list in real-time!
      if (window.refreshDashboardData) {
        window.refreshDashboardData();
      }

    } catch (e) {
      removeTypingIndicator(typingId);
      appendMessage('bot', '⚠️ Error de conexión con el servidor.');
      console.error(e);
    }
  }

  function appendMessage(sender, text) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${sender}`;
    bubble.innerHTML = `
      <div>${escapeHtml(text)}</div>
      <div class="chat-meta">${sender === 'user' ? 'Tú' : 'Agente IA'} • Justo ahora</div>
    `;
    chatContainer.appendChild(bubble);
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  function appendBotResponse(markdownText, analysis) {
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble bot';
    
    // Simple markdown format
    let formatted = formatMarkdown(markdownText);
    
    // Add analysis badge if hot lead or high intent
    let analysisTag = '';
    if (analysis && analysis.intent_score >= 0.75) {
      analysisTag = `
        <div style="margin-top: 8px; padding: 6px 10px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239,68,68,0.3); border-radius: 6px; font-size: 11px; color: #fca5a5;">
          🔥 <strong>Detección IA:</strong> ${analysis.intent} (Score: ${(analysis.intent_score * 100).toFixed(0)}%)
          ${analysis.status ? `• Estado: <strong>${analysis.status}</strong>` : ''}
        </div>
      `;
    }

    bubble.innerHTML = `
      <div>${formatted}</div>
      ${analysisTag}
      <div class="chat-meta">Agente IA CTT • Justo ahora</div>
    `;
    chatContainer.appendChild(bubble);
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  function showTypingIndicator() {
    const id = 'typing_' + Date.now();
    const ind = document.createElement('div');
    ind.id = id;
    ind.className = 'chat-bubble bot';
    ind.style.fontStyle = 'italic';
    ind.style.color = '#94a3b8';
    ind.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Asesor CTT está escribiendo...';
    chatContainer.appendChild(ind);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return id;
  }

  function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function escapeHtml(string) {
    return String(string).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function formatMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Bullet points
    html = html.replace(/\n• (.*?)/g, '<br>• $1');
    html = html.replace(/\n(\d+️⃣|\d+\.) (.*?)/g, '<br>$1 $2');
    // Links [title](url)
    html = html.replace(/\[(.*?)\]\((https?:\/\/.*?)\)/g, '<a href="$2" target="_blank" style="color: #38bdf8; text-decoration: underline; font-weight: 600;">$1</a>');
    // Newlines
    html = html.replace(/\n/g, '<br>');
    return html;
  }
}
