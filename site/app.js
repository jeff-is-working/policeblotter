/* Thurston County Police Blotter - static client.
 *
 * Loads partitioned JSON from ../data/ and filters by DAY and LOCATION only.
 * There is intentionally no name search: the data files carry no name field,
 * and this client exposes no name input. Keep it that way.
 */
'use strict';

// At deploy time the Pages build copies data/ to ./data alongside index.html.
const DATA_BASE = 'data';
const state = { index: null, source: null, rows: [] };

const $ = (id) => document.getElementById(id);

async function loadIndex() {
  const res = await fetch(`${DATA_BASE}/index.json`, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`index.json ${res.status}`);
  return res.json();
}

const ALL_SOURCES = '__all__';

function populateSources(index) {
  const sel = $('source');
  sel.innerHTML = '';
  // "Show all" aggregates every source; it is the default selection.
  const allOpt = document.createElement('option');
  allOpt.value = ALL_SOURCES;
  allOpt.textContent = 'Show all sources';
  sel.appendChild(allOpt);
  Object.keys(index).forEach((src) => {
    const opt = document.createElement('option');
    opt.value = src;
    opt.textContent = src;
    sel.appendChild(opt);
  });
}

async function loadPartitions(paths) {
  const all = [];
  for (const path of paths) {
    const res = await fetch(`${DATA_BASE}/${path}`, { cache: 'no-cache' });
    if (res.ok) all.push(...(await res.json()));
  }
  return all;
}

async function loadSource(source) {
  const sources = source === ALL_SOURCES ? Object.keys(state.index) : [source];
  const paths = sources.flatMap((src) => (state.index[src] || []).map((p) => p.path));
  const all = await loadPartitions(paths);
  // Newest first so "show all" opens on the most recent activity.
  all.sort((a, b) => (b.datetime || '').localeCompare(a.datetime || ''));
  state.source = source;
  state.rows = all;
  refreshCityList(all);
}

function refreshCityList(rows) {
  const cities = [...new Set(rows.map((r) => r.city).filter(Boolean))].sort();
  const dl = $('cities');
  dl.innerHTML = '';
  cities.forEach((c) => {
    const o = document.createElement('option');
    o.value = c;
    dl.appendChild(o);
  });
}

function applyFilters() {
  const date = $('date').value; // yyyy-mm-dd or ''
  const loc = $('city').value.trim().toLowerCase();
  let rows = state.rows;
  if (date) rows = rows.filter((r) => (r.datetime || '').slice(0, 10) === date);
  if (loc) {
    rows = rows.filter(
      (r) =>
        (r.city || '').toLowerCase().includes(loc) ||
        (r.location_block || '').toLowerCase().includes(loc)
    );
  }
  render(rows);
}

function render(rows) {
  const tbody = $('results').querySelector('tbody');
  tbody.innerHTML = '';
  rows.slice(0, 2000).forEach((r) => {
    const tr = document.createElement('tr');
    for (const val of [
      (r.datetime || '').replace('T', ' '),
      r.agency || '',
      r.type || '',
      r.nature || '',
      r.location_block || '',
      r.city || '',
    ]) {
      const td = document.createElement('td');
      td.textContent = val;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  });
  $('results').hidden = rows.length === 0;
  const shown = Math.min(rows.length, 2000);
  $('status').textContent = rows.length
    ? `Showing ${shown} of ${rows.length} record${rows.length === 1 ? '' : 's'}.`
    : 'No records match those filters.';
}

async function init() {
  try {
    state.index = await loadIndex();
    if (!Object.keys(state.index).length) {
      $('status').textContent = 'No data is available yet.';
      return;
    }
    populateSources(state.index);
    await loadSource($('source').value);
    applyFilters();
    $('source').addEventListener('change', async (e) => {
      $('status').textContent = 'Loading…';
      await loadSource(e.target.value);
      applyFilters();
    });
    $('filters').addEventListener('submit', (e) => {
      e.preventDefault();
      applyFilters();
    });
  } catch (err) {
    $('status').textContent = `Could not load data: ${err.message}`;
  }
}

init();
