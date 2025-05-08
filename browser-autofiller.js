(function () {
  const state = {
    childrenByChickAndEnd: {},
    totalMatches: 0
  };

  const schoolHolidays = {
    "2024-2025": {
      "October Holidays": ["28/10/2024", "01/11/2024"],
      "Christmas Holidays": ["23/12/2024", "03/01/2025"],
      "February Holidays": ["17/02/2025", "21/02/2025"],
      "Easter Holidays": ["14/04/2025", "25/04/2025"]
    },
    "2025-2026": {
      "October Holidays": ["27/10/2025", "31/10/2025"],
      "Christmas Holidays": ["22/12/2025", "02/01/2026"],
      "February Holidays": ["16/02/2026", "20/02/2026"],
      "Easter Holidays": ["30/03/2026", "10/04/2026"]
    }
  };

  createUI();

  function processCSV(file) {
    const reader = new FileReader();
    reader.onload = function (e) {
      const csv = e.target.result;
      const data = parseCSV(csv);

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
    processNextRow(rows, 0, null);
  }

  function processNextRow(rows, i, previousChick) {
    if (i >= rows.length) return updateStatus(`Finished. ${state.totalMatches} rows matched`, 'success');

    const row = rows[i];
    const chick = row.querySelector('input[name*="[chick_number]"]')?.value.trim();
    const claimUntil = row.querySelector('input[name*="[date_to]"]')?.value.trim();

    if (!chick || !claimUntil) {
      console.warn("Missing CHICK or Claim Until at row", i);
      return processNextRow(rows, i + 1, previousChick);
    }

    // Add border between different children
    if (chick !== previousChick) {
      row.style.borderTop = '3px solid #444';
    }

    const key = chick + "|" + claimUntil;
    const candidates = state.childrenByChickAndEnd[key] || [];

    if (candidates.length === 1) {
      fillFields(row, candidates[0]);
      state.totalMatches++;
      candidates.splice(0, 1);
    } else if (candidates.length > 1) {
      const inputStart = row.querySelector('input[name*="[date_from]"]');
      const startValue = inputStart?.value.trim();
      const exact = candidates.find(c => c['Funding Start']?.trim() === startValue);

      const toFill = exact || candidates[0];
      fillFields(row, toFill);
      state.totalMatches++;
      candidates.splice(candidates.indexOf(toFill), 1);
    }

    setTimeout(() => processNextRow(rows, i + 1, chick), 80);
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

    const startDate = parseDate(data['Funding Start']);
    const endDate = parseDate(data['Claim Until']);
    const isBasePeriod = data.Note?.includes('Base');
    const isOldPeriod = endDate && ((new Date() - endDate) / (1000 * 60 * 60 * 24) > 90); // older than 3 months

    // Visual style
    if (isBasePeriod) {
      row.style.fontWeight = 'bold';
      row.style.borderLeft = '4px solid purple';
    } else if (isOldPeriod) {
      row.style.backgroundColor = 'rgba(255, 0, 0, 0.15)'; // red
    } else {
      row.style.backgroundColor = 'rgba(76, 175, 80, 0.15)'; // green
    }

    const lastTd = row.querySelector('td:last-child');
    if (!lastTd) return;

    // Notes badge
    if (data.Note && data.Note.includes(';')) {
      const note = data.Note.split(';').slice(1).join(';').trim();
      if (note) {
        const badge = document.createElement('div');
        badge.textContent = note;
        badge.style.cssText = 'color:#fff;background:#ff9800;padding:2px 6px;margin-top:4px;border-radius:4px;display:inline-block;font-size:12px';
        lastTd.appendChild(badge);
      }
    }

    // Holiday badge
    if (startDate) {
      const holiday = getHolidayName(startDate);
      if (holiday) {
        const badge = document.createElement('div');
        badge.textContent = holiday;
        badge.style.cssText = 'color:#fff;background:#00bcd4;padding:2px 6px;margin-top:4px;margin-left:4px;border-radius:4px;display:inline-block;font-size:12px';
        lastTd.appendChild(badge);
      }
    }
  }

  function getHolidayName(date) {
    const summerStart = getFirstMondayBeforeOrOn(new Date(date.getFullYear(), 6, 1));
    const summerEnd = getFirstMondayBeforeOrOn(new Date(date.getFullYear(), 8, 1));
    if (date >= summerStart && date < summerEnd) return "Summer Holidays";

    for (const year of Object.keys(schoolHolidays)) {
      for (const [name, [startStr, endStr]] of Object.entries(schoolHolidays[year])) {
        const start = parseDate(startStr);
        const end = parseDate(endStr);
        if (date >= start && date <= end) return name;
      }
    }
    return null;
  }

  function getFirstMondayBeforeOrOn(date) {
    const result = new Date(date);
    while (result.getDay() !== 1) {
      result.setDate(result.getDate() - 1);
    }
    return result;
  }

  function parseDate(str) {
    const [dd, mm, yyyy] = str.split('/');
    return new Date(`${yyyy}-${mm}-${dd}`);
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
