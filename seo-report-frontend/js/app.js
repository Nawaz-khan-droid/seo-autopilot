let activeTab = 'home';

function showTab(tabId) {
  activeTab = tabId;
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('[data-tab]').forEach(el => el.classList.remove('active'));
  const content = document.getElementById(`tab-${tabId}`);
  const btn = document.querySelector(`[data-tab="${tabId}"]`);
  if (content) content.classList.add('active');
  if (btn) btn.classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showStatus(id, msg, type = 'info') {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.className = `status-msg ${type}`;
}

function showResults(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('show');
}

function showProgress(pct, prefix = '') {
  const fill = document.getElementById(`${prefix}progress-fill`);
  const container = document.getElementById(`${prefix}progress-container`);
  if (fill) fill.style.width = `${Math.min(100, Math.max(0, pct))}%`;
  if (container) container.classList.add('active');
}

function hideProgress(prefix = '') {
  const container = document.getElementById(`${prefix}progress-container`);
  if (container) container.classList.remove('active');
}

function cycleProgressMessage(messages, interval = 2500, prefix = '') {
  let i = 0;
  const el = document.getElementById(`${prefix}progress-msg`);
  if (!el) return null;
  el.textContent = messages[0];
  const timer = setInterval(() => {
    i = (i + 1) % messages.length;
    el.textContent = messages[i];
  }, interval);
  return timer;
}

function renderMetricsBar(containerId, metrics) {
  const bar = document.getElementById(containerId);
  if (!bar) return;

  const cards = [];
  const addCard = (value, label) => {
    if (value !== null && value !== undefined && value !== '' && value !== '—') {
      cards.push(`<div class="demo-metric"><div class="dm-value">${value}</div><div class="dm-label">${label}</div></div>`);
    }
  };

  addCard((metrics.health_score || metrics.healthScore) + '/100', 'Technical Health');
  addCard(metrics.pages_audited || metrics.pagesAudited, 'Pages Audited');
  addCard(metrics.missing_h1_count ?? metrics.missingH1, 'Missing H1');
  addCard(metrics.missing_meta_tags ?? metrics.missingMeta, 'Missing Meta');
  addCard(metrics.missing_alt_tags ?? metrics.missingAlt, 'Missing Alt');
  addCard(metrics.total_images_found ?? metrics.totalImagesFound, 'Images Found');
  addCard(metrics.thin_pages_detected ?? metrics.thinPages, 'Thin Pages');
  addCard(metrics.keywords_tracked, 'Keywords Tracked');
  addCard(metrics.rankings_top_3, 'Top 3 Rankings');
  addCard(metrics.rankings_top_10, 'Top 10 Rankings');
  if (metrics.backlinks_count && metrics.backlinks_count !== 'No Data' && metrics.backlinks_count !== 'Data Pending') {
    addCard(metrics.backlinks_count, 'Backlinks');
  }

  if (cards.length === 0) {
    bar.style.display = 'none';
    return;
  }
  bar.style.display = 'grid';
  bar.innerHTML = cards.join('');
}

function updatePreview(title, desc, url, extra) {
  extra = extra || {};
  const empty = document.getElementById('preview-empty');
  const meta = document.getElementById('preview-meta');
  if (empty) empty.style.display = 'none';
  if (meta) meta.style.display = 'block';
  document.getElementById('preview-title').textContent = title || 'Untitled Page';
  document.getElementById('preview-desc').textContent = desc || 'No description detected';
  document.getElementById('preview-siteurl').textContent = url || 'https://';
  const nicheEl = document.getElementById('preview-niche');
  if (nicheEl) nicheEl.textContent = extra.niche || '—';
  document.getElementById('preview-health').textContent = extra.health || '—';
  document.getElementById('preview-pages').textContent = extra.pages || '—';
  const h1El = document.getElementById('preview-missing-h1');
  if (h1El) h1El.textContent = extra.missing_h1 ?? '—';
  const metaEl = document.getElementById('preview-missing-meta');
  if (metaEl) metaEl.textContent = extra.missing_meta ?? '—';
  const altEl = document.getElementById('preview-missing-alt');
  if (altEl) altEl.textContent = extra.missing_alt ?? '—';
  const imgEl = document.getElementById('preview-images-found');
  if (imgEl) imgEl.textContent = extra.images_found ?? '—';
}

function resetPreview() {
  const empty = document.getElementById('preview-empty');
  const meta = document.getElementById('preview-meta');
  if (empty) empty.style.display = 'flex';
  if (meta) meta.style.display = 'none';
}

/* ── API Settings ── */
function toggleSettings() {
  const modal = document.getElementById('api-settings-modal');
  const input = document.getElementById('api-url-input');
  const status = document.getElementById('api-settings-status');
  if (modal.style.display === 'none') {
    modal.style.display = 'flex';
    input.value = localStorage.getItem('seo_api_url') || '';
    status.textContent = '';
  } else {
    modal.style.display = 'none';
  }
}

async function saveApiUrl() {
  const input = document.getElementById('api-url-input');
  const status = document.getElementById('api-settings-status');
  const url = input.value.trim().replace(/\/+$/, '');
  if (!url) { status.textContent = 'Enter a URL first'; status.style.color = 'red'; return; }
  API.setBaseUrl(url);
  status.textContent = 'Testing connection...';
  status.style.color = 'var(--gray)';
  try {
    const r = await API.health();
    if (r.status === 'ok') {
      status.textContent = 'Connected! API is running.';
      status.style.color = 'var(--green)';
      setTimeout(() => { document.getElementById('api-settings-modal').style.display = 'none'; }, 1200);
    } else {
      status.textContent = 'Unexpected response. Check the URL.';
      status.style.color = 'orange';
    }
  } catch (e) {
    status.textContent = 'Cannot connect. Is the Codespace running?';
    status.style.color = 'red';
  }
}

function clearApiUrl() {
  localStorage.removeItem('seo_api_url');
  API._storedUrl = null;
  document.getElementById('api-url-input').value = '';
  document.getElementById('api-settings-status').textContent = 'Cleared. Will use same origin.';
  document.getElementById('api-settings-status').style.color = 'var(--gray)';
}

/* ── Initialization ── */
document.addEventListener('DOMContentLoaded', () => {
  /* Auto-detect API URL: if no saved URL and health check fails, show settings */
  (async function autoDetectApi() {
    if (localStorage.getItem('seo_api_url')) return; // already configured
    try {
      const r = await fetch(window.location.origin + '/api/health', { signal: AbortSignal.timeout(3000) });
      if (!r.ok) throw new Error('not ok');
      const data = await r.json();
      if (data.status === 'ok') return; // same-origin API works
    } catch {
      // health check failed — show settings modal
      setTimeout(() => toggleSettings(), 500);
    }
  })();

  /* Mobile nav toggle */
  const navToggle = document.getElementById('nav-toggle');
  const mainNav = document.getElementById('main-nav');
  if (navToggle && mainNav) {
    navToggle.addEventListener('click', () => {
      navToggle.classList.toggle('open');
      mainNav.style.display = navToggle.classList.contains('open') ? 'flex' : '';
      if (navToggle.classList.contains('open')) {
        mainNav.style.flexDirection = 'column';
        mainNav.style.position = 'absolute';
        mainNav.style.top = '56px';
        mainNav.style.left = '0';
        mainNav.style.right = '0';
        mainNav.style.background = '#fff';
        mainNav.style.padding = '8px 16px';
        mainNav.style.borderBottom = '1px solid var(--border)';
        mainNav.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
        mainNav.style.zIndex = '99';
      }
    });
    /* Close nav when a link is clicked */
    mainNav.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        navToggle.classList.remove('open');
        mainNav.style.display = '';
        mainNav.style.flexDirection = '';
        mainNav.style.position = '';
        mainNav.style.top = '';
        mainNav.style.left = '';
        mainNav.style.right = '';
        mainNav.style.background = '';
        mainNav.style.padding = '';
        mainNav.style.borderBottom = '';
        mainNav.style.boxShadow = '';
        mainNav.style.zIndex = '';
      });
    });
    /* Auto-close on resize to desktop */
    window.addEventListener('resize', () => {
      if (window.innerWidth >= 900) {
        navToggle.classList.remove('open');
        mainNav.style.cssText = '';
      }
    });
  }

  /* FAQ accordion */
  document.querySelectorAll('.faq-question').forEach(q => {
    q.addEventListener('click', () => {
      const item = q.closest('.faq-item');
      if (item) item.classList.toggle('open');
    });
  });

  /* Tab navigation */
  document.querySelectorAll('[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => showTab(btn.dataset.tab));
  });

  /* Hero CTA buttons */
  const heroDemo = document.getElementById('hero-demo');
  if (heroDemo) {
    heroDemo.addEventListener('click', async (e) => {
      e.preventDefault();
      showTab('demo');
      setTimeout(() => runDemo(), 300);
    });
  }

  const heroAudit = document.getElementById('hero-audit');
  if (heroAudit) {
    heroAudit.addEventListener('click', (e) => {
      e.preventDefault();
      showTab('audit');
    });
  }

  /* Audit form */
  const auditForm = document.getElementById('audit-form');
  if (auditForm) {
    auditForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      await runAudit();
    });
  }

  /* Report form — belt-and-suspenders prevent submit */
  const reportForm = document.getElementById('report-form');
  if (reportForm) {
    reportForm.addEventListener('submit', (e) => e.preventDefault());
  }

  /* Audit URL preview */
  const auditUrl = document.getElementById('audit-url');
  if (auditUrl) {
    auditUrl.addEventListener('input', () => {
      const val = auditUrl.value.trim();
      if (val) {
        document.getElementById('preview-url').textContent = val;
        updatePreview('Loading...', 'Awaiting crawl results', val, {});
      } else {
        resetPreview();
      }
    });
  }

  /* Brainstorm filters */
  const phaseSel = document.getElementById('brainstorm-phase');
  const catSel = document.getElementById('brainstorm-category');
  if (phaseSel) phaseSel.addEventListener('change', renderBrainstorm);
  if (catSel) catSel.addEventListener('change', renderBrainstorm);
  renderBrainstorm();
});

/* ── DEMO – Live Audit on Any URL ── */
async function runDemo() {
  const urlInput = document.getElementById('demo-url');
  const url = urlInput ? urlInput.value.trim() : '';

  if (!url) {
    showStatus('demo-status', 'Please enter a URL to analyze.', 'error');
    return;
  }
  if (!url.startsWith('http')) {
    showStatus('demo-status', 'Please enter a valid URL starting with https://', 'error');
    return;
  }

  showStatus('demo-status', `Starting live audit of ${url}...`, 'info');
  hideProgress('demo-');
  showProgress(10, 'demo-');

  const messages = [
    'Launching headless browser for JS rendering...',
    'Extracting on-page SEO elements (title, meta, H1, images)...',
    'Fetching PageSpeed Insights (Core Web Vitals)...',
    'Classifying business niche via multi-signal AI...',
    'Compiling report data...',
  ];
  const timer = cycleProgressMessage(messages, 3000, 'demo-');

  try {
    showProgress(10, 'demo-');
    const data = await API.runDemoWithPolling(url, (progress) => {
      document.getElementById('demo-progress-msg').textContent = progress;
    });
    showProgress(80, 'demo-');
    if (timer) clearInterval(timer);

    const metrics = data.metrics || {};
    const siteUrl = metrics.url || url;

    document.getElementById('demo-progress-msg').textContent = `Audit complete — ${data.client || siteUrl}`;
    showStatus('demo-status', `Live audit of ${siteUrl} completed successfully.`, 'success');
    showResults('demo-results');

    // Generate dynamic suggestions from actual issues
    const issues = data.issues || [];
    const suggestionsEl = document.getElementById('demo-suggestions');
    if (suggestionsEl) {
      if (issues.length === 0) {
        suggestionsEl.innerHTML = '<p style="color:var(--green);font-weight:500">No critical issues found. The page passes all checked SEO rules.</p>';
      } else {
        const p1 = issues.filter(i => i.severity === 'Critical' || i.severity === 'High');
        const p2 = issues.filter(i => i.severity === 'Warning' || i.severity === 'Medium');
        let html = '<ul style="font-size:13px;line-height:1.8;padding-left:20px;color:var(--body)">';
        if (p1.length) {
          html += `<li><strong>P1 — High (${p1.length} issues):</strong> ${p1.slice(0, 3).map(i => i.issue_text).join('; ')}.</li>`;
        }
        if (p2.length) {
          html += `<li><strong>P2 — Medium (${p2.length} issues):</strong> ${p2.slice(0, 3).map(i => i.issue_text).join('; ')}.</li>`;
        }
        if (!p1.length && !p2.length) {
          html += '<li>All issues are informational — no action required.</li>';
        }
        html += '</ul>';
        suggestionsEl.innerHTML = html;
      }
    }
    showProgress(100, 'demo-');

    renderMetricsBar('demo-metrics', metrics);
    updatePreview(
      metrics.title || siteUrl,
      metrics.meta_description || `Technical audit results for ${siteUrl}`,
      siteUrl,
      {
        niche: data.niche || '—',
        health: (metrics.health_score || '—') + '/100',
        pages: metrics.pages_audited || '—',
        missing_h1: metrics.missing_h1_count ?? '—',
        missing_meta: metrics.missing_meta_tags ?? '—',
        missing_alt: metrics.missing_alt_tags ?? '—',
        images_found: metrics.total_images_found ?? '—',
      }
    );
  } catch (err) {
    if (timer) clearInterval(timer);
    document.getElementById('demo-progress-msg').textContent = '';
    showStatus('demo-status', `Audit failed: ${err.message}`, 'error');
    hideProgress('demo-');
    showProgress(0, 'demo-');
  }
}

/* ── SEO AUDIT ── */
async function runAudit() {
  const url = document.getElementById('audit-url').value.trim();
  const mode = document.getElementById('audit-mode').value;
  const sheetUrl = document.getElementById('audit-sheet').value.trim();
  const month = document.getElementById('audit-month').value.trim();

  if (!url) {
    showStatus('audit-status', 'Please enter a website URL to begin the audit.', 'error');
    return;
  }

  /* ── Progress Buffer: hide old results ── */
  hideProgress('audit-');
  document.getElementById('audit-results').classList.remove('show');
  document.getElementById('audit-metrics-bar').style.display = 'none';
  showStatus('audit-status', 'Initializing audit pipeline...', 'info');
  showProgress(10, 'audit-');

  const progressMessages = [
    'Running local SEO-Analyzer audit engine nodes...',
    'Evaluating semantic content readability vectors...',
    'Scanning metadata and heading tags...',
    'Checking schema markup and structured data...',
    'Assessing answer engine citation readiness...',
    'Writing production-grade implementation roadmap file...',
  ];
  const timer = cycleProgressMessage(progressMessages, 2200, 'audit-');

  try {
    const data = await API.runAudit(url, sheetUrl, mode, month);
    showProgress(90, 'audit-');
    if (timer) clearInterval(timer);
    document.getElementById('audit-progress-msg').textContent = '';

    if (data.success || data.generated?.length) {
      const gen = (data.generated || []).filter(f => f.type === 'audit');
      showStatus('audit-status', `Audit complete — ${gen.length} document(s) generated.`, 'success');
      renderFiles('audit-files', gen);
      document.getElementById('audit-results').classList.add('show');

      const metrics = data.metrics || {};
      renderMetricsBar('audit-metrics-bar', metrics);
      updatePreview(
        data.client || url,
        `Technical audit for ${url}`,
        url,
        {
          niche: data.niche || '—',
          health: (metrics.health_score || '—') + '/100',
          pages: metrics.pages_audited || '—',
          missing_h1: metrics.missing_h1_count ?? '—',
          missing_meta: metrics.missing_meta_tags ?? '—',
          missing_alt: metrics.missing_alt_tags ?? '—',
          images_found: metrics.total_images_found ?? '—',
        }
      );
    } else {
      showStatus('audit-status', `Audit finished with cautions: ${(data.errors || []).join('; ')}`, 'warn');
      if (data.generated?.length) {
        renderFiles('audit-files', (data.generated || []).filter(f => f.type === 'audit'));
        document.getElementById('audit-results').classList.add('show');
      }
    }
    showProgress(100, 'audit-');
  } catch (err) {
    if (timer) clearInterval(timer);
    document.getElementById('audit-progress-msg').textContent = '';
    showStatus('audit-status', `Audit could not complete: ${err.message}`, 'error');
    hideProgress('audit-');
    showProgress(0, 'audit-');
  }
}

/* ── MONTHLY REPORT ── */
async function runReport() {
  const url = document.getElementById('report-url').value.trim();
  const sheetUrl = document.getElementById('report-sheet').value.trim();
  const month = document.getElementById('report-month').value.trim();

  if (!url) {
    showStatus('report-status', 'Please enter a client website URL.', 'error');
    return;
  }

  hideProgress('report-');
  document.getElementById('report-results').classList.remove('show');
  showStatus('report-status', 'Initializing report generation pipeline...', 'info');
  showProgress(10, 'report-');

  const progressMessages = [
    'Running full technical audit...',
    'Building technical SEO audit document...',
    'Generating monthly SEO report...',
    'Compiling action plan...',
    'Finalizing all deliverables...',
  ];
  const timer = cycleProgressMessage(progressMessages, 2200, 'report-');

  try {
    const data = await API.runAudit(url, sheetUrl, 'single', month);
    showProgress(90, 'report-');
    if (timer) clearInterval(timer);
    document.getElementById('report-progress-msg').textContent = '';

    const allGenerated = (data.generated || []);
    const errors = (data.errors || []).filter(e => e);
    if (allGenerated.length) {
      showStatus('report-status', errors.length
        ? `Generated ${allGenerated.length} document(s). Cautions: ${errors.join('; ')}`
        : `${allGenerated.length} document(s) generated successfully.`, errors.length ? 'warn' : 'success');
      renderFiles('report-files', allGenerated);
      document.getElementById('report-results').classList.add('show');
    } else {
      showStatus('report-status', errors.length ? errors.join('; ') : 'No documents were generated.', 'error');
    }
    showProgress(100, 'report-');
  } catch (err) {
    if (timer) clearInterval(timer);
    document.getElementById('report-progress-msg').textContent = '';
    showStatus('report-status', `Report generation failed: ${err.message}`, 'error');
    hideProgress('report-');
    showProgress(0, 'report-');
  }
}

/* ── BRAINSTORM ── */
function renderBrainstorm() {
  const container = document.getElementById('brainstorm-list');
  if (!container) return;
  const phaseFilter = document.getElementById('brainstorm-phase')?.value || 'all';
  const catFilter = document.getElementById('brainstorm-category')?.value || 'all';

  const filtered = BRAINSTORM.ideas.filter(i =>
    (phaseFilter === 'all' || i.phase === phaseFilter) &&
    (catFilter === 'all' || i.category === catFilter)
  );

  const phase = id => BRAINSTORM.phases[id];
  const cat = id => BRAINSTORM.categories[id];
  const ef = id => BRAINSTORM.efforts[id];

  container.innerHTML = filtered.map(idea => {
    const p = phase(idea.phase);
    const c = cat(idea.category);
    const e = ef(idea.effort);
    const pr = BRAINSTORM.priorities[idea.priority];
    const idSafe = idea.id.replace(/-/g, '_');

    return `<div class="brainstorm-card" id="bc-${idSafe}">
      <div class="bc-header">
        <div class="bc-badges">
          <span class="bc-phase" style="background:${p.bg};color:${p.color};border-color:${p.border}">${p.emoji} ${p.label}</span>
          <span class="bc-cat" style="background:${c.bg};color:${c.color}">${c.label}</span>
          <span class="bc-effort" style="background:${e.bg};color:${e.color}">${e.icon} ${e.label}</span>
          <span style="color:#64748b;font-size:12px">⏱ ${idea.timeline}</span>
          <span class="bc-priority" style="${pr.css}">${pr.label}</span>
        </div>
        <h3 class="bc-title">${idea.title}</h3>
        <p class="bc-tagline">${idea.tagline}</p>
      </div>
      <div class="bc-scores">
        <div class="sc"><span class="sc-val" style="color:#059669">${idea.impact}/10</span><span class="sc-lbl">Impact</span></div>
        <div class="sc"><span class="sc-val" style="color:#0891b2">${idea.feasibility}/10</span><span class="sc-lbl">Feasibility</span></div>
      </div>
      <button class="bc-toggle" onclick="toggleBrainstormDetail('${idea.id}')">
        <span class="bc-toggle-text" id="bt-${idSafe}">Show Details</span>
        <span class="bc-toggle-icon" id="bi-${idSafe}">▾</span>
      </button>
      <div class="bc-detail" id="bd-${idSafe}">
        <p class="bc-desc">${idea.desc}</p>
        <div class="bc-section"><strong>✅ Benefits</strong><ul>${idea.benefits.map(b => `<li>${b}</li>`).join('')}</ul></div>
        <div class="bc-tags">${(idea.tags || []).map(t => `<span class="bc-tag">${t}</span>`).join('')}</div>
      </div>
    </div>`;
  }).join('');

  document.getElementById('brainstorm-count').textContent = `Showing ${filtered.length} of ${BRAINSTORM.ideas.length} ideas`;
}

function toggleBrainstormDetail(id) {
  const detail = document.getElementById(`bd-${id.replace(/-/g, '_')}`);
  const text = document.getElementById(`bt-${id.replace(/-/g, '_')}`);
  const icon = document.getElementById(`bi-${id.replace(/-/g, '_')}`);
  if (!detail) return;
  const isOpen = detail.style.display === 'block';
  detail.style.display = isOpen ? 'none' : 'block';
  if (text) text.textContent = isOpen ? 'Show Details' : 'Hide Details';
  if (icon) icon.textContent = isOpen ? '▾' : '▴';
}

function renderFiles(containerId, files) {
  const list = document.getElementById(containerId);
  if (!list) return;
  if (!files || !files.length) {
    list.innerHTML = '<li style="color:var(--gray);font-size:13px">No files generated.</li>';
    return;
  }
  list.innerHTML = files.map(f => {
    const size = f.size_bytes > 1024 ? `${(f.size_bytes / 1024).toFixed(0)} KB` : `${f.size_bytes} B`;
    let icon, label, desc;
    if (f.type === 'audit') {
      icon = '🛡️';
      label = 'Technical SEO Audit Report';
      desc = 'One-shot technical deep dive';
    } else if (f.type === 'report') {
      icon = '📄';
      label = 'Monthly SEO Report';
      desc = 'Client facing report';
    } else if (f.type === 'plan') {
      icon = '📋';
      label = 'SEO Action Plan';
      desc = 'Internal team roadmap';
    } else {
      icon = '📎';
      label = f.type.charAt(0).toUpperCase() + f.type.slice(1);
      desc = '';
    }
    return `<li>
      <div class="file-info">
        <span class="file-icon">${icon}</span>
        <div class="file-text">
          <div class="file-name" title="${f.filename}">${label}</div>
          <div class="file-size">${size} &middot; Word DOCX &middot; ${desc}</div>
        </div>
      </div>
      <a href="${API.downloadUrl(f.filename)}" class="download-link" target="_blank">Download</a>
    </li>`;
  }).join('');
}
