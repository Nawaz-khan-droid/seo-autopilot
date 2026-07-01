const API = {
  _storedUrl: null,

  get BASE_URL() {
    if (this._storedUrl) return this._storedUrl;
    const saved = localStorage.getItem('seo_api_url');
    if (saved) {
      this._storedUrl = saved.replace(/\/+$/, '');
      return this._storedUrl;
    }
    // Default: assume API is on same origin ( Codespaces self-hosted mode )
    return window.location.origin;
  },

  setBaseUrl(url) {
    url = (url || '').trim().replace(/\/+$/, '');
    if (url) {
      localStorage.setItem('seo_api_url', url);
      this._storedUrl = url;
    } else {
      localStorage.removeItem('seo_api_url');
      this._storedUrl = null;
    }
  },

  async health() {
    const r = await fetch(this.BASE_URL + '/api/health');
    return r.json();
  },

  async clients() {
    const r = await fetch(this.BASE_URL + '/api/clients');
    return r.json();
  },

  async generateReport(clientName, month, type = 'both') {
    const r = await fetch(this.BASE_URL + '/api/reports/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_name: clientName, report_month: month, type }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    return r.json();
  },

  async runAudit(url, sheetUrl = '', mode = 'single', month = '') {
    const r = await fetch(this.BASE_URL + '/api/audit/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, sheet_url: sheetUrl, mode, report_month: month }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    return r.json();
  },

  async fetchDemo(url) {
    const r = await fetch(this.BASE_URL + '/api/demo/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url: url}),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    return r.json();
  },

  async pollDemoStatus(jobId) {
    const r = await fetch(this.BASE_URL + '/api/demo/status/' + jobId);
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    return r.json();
  },

  async runDemoWithPolling(url, onProgress, maxWaitMs = 300000) {
    const start = await this.fetchDemo(url);
    const jobId = start.job_id;
    const deadline = Date.now() + maxWaitMs;
    while (Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 2000));
      const poll = await this.pollDemoStatus(jobId);
      if (poll.status === 'done') return poll.result;
      if (poll.status === 'error') throw new Error(poll.error || 'Audit failed');
      if (onProgress) onProgress(poll.progress || 'Processing...');
    }
    throw new Error('Audit timed out after 5 minutes');
  },

  downloadUrl(filename) {
    return this.BASE_URL + '/api/reports/download/' + encodeURIComponent(filename);
  },
};
