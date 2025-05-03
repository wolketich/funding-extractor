(function () {
  const state = {
    childrenByChickAndEnd: {},
    totalMatches: 0
  };

  createUI();

  function processCSV(file) {
    const reader = new FileReader();
    reader.onload = function (e) {
      const csv = e.target.result;
      const data = parseCSV(csv);

      // Index by CHICK + Claim Until
      data.forEach(row => {
        const key = row['CHICK'].trim() + "|" + row['Claim Until'].trim();
        if (!state.childrenByChickAndEnd[key]) {
          state.childrenByChickAndEnd[key] = [];
        }
        state.childrenByChickAndEnd[key].push(row);
      });

      processTableRows();
    };

    reader.readAsText(file);
  }

  function parseCSV(csv) {
    const lines = csv.trim().split('\n');
    const headers = lines[0].split(',').map(h => h.trim());
    return lines.slice(1).map(line => {
      const values = line.split(',').map(v => v.trim());
      const row = {};
      headers.forEach((header, i) => {
        row[header] = values[i] || '';
      });
      return row;
    });
  }

  function processTableRows() {
    const table = document.querySelector("table.table.table-striped");
    if (!table) return updateStatus('Table not found', 'error');

    const rows = table.querySelectorAll('tbody > tr');
    if (!rows.length) return updateStatus('No rows found', 'error');

    updateStatus(`Found ${rows.length} rows`, 'info');
    processNextRow(rows, 0);
  }

  function processNextRow(rows, i) {
    if (i >= rows.length) return updateStatus(`Finished. ${state.totalMatches} rows matched`, 'success');

    const row = rows[i];
    const chick = row.querySelector('input[name*="[chick_number]"]')?.value.trim();
    const claimUntil = row.querySelector('input[name*="[date_to]"]')?.value.trim();

    if (!chick || !claimUntil) {
      console.warn("Missing CHICK or Claim Until at row", i);
      return processNextRow(rows, i + 1);
    }

    const key = chick + "|" + claimUntil;
    const candidates = state.childrenByChickAndEnd[key] || [];

    if (candidates.length === 1) {
      fillFields(row, candidates[0]);
      state.totalMatches++;
    } else if (candidates.length > 1) {
      // Pick one with matching Start date, if possible
      const inputStart = row.querySelector('input[name*="[date_from]"]');
      const startValue = inputStart?.value.trim();
      const exact = candidates.find(c => c['Funding Start']?.trim() === startValue);

      if (exact) {
        fillFields(row, exact);
        state.totalMatches++;
      } else {
        fillFields(row, candidates[0]); // fallback to first
        state.totalMatches++;
      }
    }

    setTimeout(() => processNextRow(rows, i + 1), 80);
  }

  function fillFields(row, data) {
    const setInput = (selector, value) => {
      const el = row.querySelector(selector);
      if (el) {
        el.value = value || '';
        el.dispatchEvent(new Event('change', { bubbles: true }));
      }
    };

    setInput('input[name*="[date_from]"]', data['Funding Start']);
    setInput('input[name*="[weekly_total]"]', data['Weekly Total']);
    setInput('input[name*="[hour_rate]"]', data['Hour rate']?.replace(/[^\d.]/g, ''));
    row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    row.style.backgroundColor = 'rgba(76, 175, 80, 0.15)';
  }

  function createUI() {
    const container = document.createElement('div');
    container.style.cssText = 'position:fixed;top:20px;right:20px;padding:12px;background:#fff;border:1px solid #ccc;z-index:9999;border-radius:8px;font-family:sans-serif;box-shadow:0 0 10px rgba(0,0,0,0.2)';
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv';
    input.style.display = 'block';
    input.addEventListener('change', e => {
      if (e.target.files[0]) processCSV(e.target.files[0]);
    });

    const status = document.createElement('div');
    status.id = 'csv-autofill-status';
    status.style.marginTop = '10px';

    container.appendChild(document.createTextNode("Upload CSV:"));
    container.appendChild(input);
    container.appendChild(status);
    document.body.appendChild(container);
  }

  function updateStatus(msg, type) {
    const el = document.getElementById('csv-autofill-status');
    if (el) {
      el.textContent = msg;
      el.style.color = type === 'error' ? 'red' : type === 'success' ? 'green' : '#444';
    }
  }
})();
// This script is designed to be run in the context of a web page.
