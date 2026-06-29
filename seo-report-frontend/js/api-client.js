const API = {
  BASE_URL: 'https://jubilant-bassoon-695gwrrpvqgxf69p-8000.app.github.dev',

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

  downloadUrl(filename) {
    return this.BASE_URL + '/api/reports/download/' + encodeURIComponent(filename);
  },
};
