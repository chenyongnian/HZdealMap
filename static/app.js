const map = L.map('map').setView([30.2741, 120.1551], 11);
const info = document.getElementById('info');
let markers = [];
let markerMap = new Map();

const sumProjects = document.getElementById('sumProjects');
const sumMonth = document.getElementById('sumMonth');
const sumQuarter = document.getElementById('sumQuarter');
const sumYear = document.getElementById('sumYear');
const sumUpdated = document.getElementById('sumUpdated');

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const hzBoundary = {
  type: 'Feature',
  geometry: {
    type: 'Polygon',
    coordinates: [[
      [119.76, 30.57], [120.53, 30.57], [120.60, 30.40], [120.63, 30.23],
      [120.48, 29.95], [120.20, 29.85], [119.94, 29.90], [119.79, 30.12],
      [119.72, 30.35], [119.76, 30.57]
    ]]
  }
};

L.geoJSON(hzBoundary, {
  style: {
    color: '#38bdf8',
    weight: 2,
    fillColor: '#0ea5e9',
    fillOpacity: 0.08
  }
}).addTo(map);

function applySummary(summary) {
  sumProjects.textContent = summary.projects ?? 0;
  sumMonth.textContent = `${summary.month_total ?? 0} 套`;
  sumQuarter.textContent = `${summary.quarter_total ?? 0} 套`;
  sumYear.textContent = `${summary.year_total ?? 0} 套`;
  sumUpdated.textContent = summary.updated_at ? new Date(summary.updated_at).toLocaleString() : '-';
}

function renderMarkers(projects) {
  markers.forEach((m) => m.remove());
  markers = [];
  markerMap = new Map();
  projects.forEach((p) => {
    const marker = L.circleMarker([p.lat, p.lng], {
      radius: 6,
      color: '#334155',
      fillColor: '#22d3ee',
      fillOpacity: 0.8,
      weight: 1
    }).addTo(map);
    marker.bindTooltip(p.name);
    markers.push(marker);
    markerMap.set(p.name, marker);
  });
}

function setHighlighted(name) {
  markers.forEach((m) => {
    const active = m.getTooltip()?.getContent() === name;
    m.setStyle({
      radius: active ? 11 : 6,
      fillColor: active ? '#f97316' : '#22d3ee',
      color: active ? '#fed7aa' : '#334155'
    });
  });
}

function renderProject(project, message) {
  if (!project) {
    info.innerHTML = `<div>${message || '暂无数据'}</div>`;
    return;
  }
  setHighlighted(project.name);
  info.innerHTML = `
    <div><b>${project.name}</b>（${project.district}）</div>
    <div class="metric"><span>当月成交</span><b>${project.monthly_deals} 套</b></div>
    <div class="metric"><span>当季度成交</span><b>${project.quarterly_deals} 套</b></div>
    <div class="metric"><span>当年成交</span><b>${project.yearly_deals} 套</b></div>
    <div class="footer">来源：${project.source}<br/>更新时间：${new Date(project.updated_at).toLocaleString()}</div>
  `;
}

async function refreshSummary() {
  const res = await fetch('/api/summary');
  const data = await res.json();
  applySummary(data);
}

async function refreshProjects() {
  const res = await fetch('/api/projects/all');
  const data = await res.json();
  renderMarkers(data.projects || []);
}

let timer = null;
map.on('mousemove', (evt) => {
  if (timer) clearTimeout(timer);
  timer = setTimeout(async () => {
    const { lat, lng } = evt.latlng;
    const res = await fetch(`/api/projects?lat=${lat}&lng=${lng}`);
    const data = await res.json();
    renderProject(data.project, data.message);
  }, 120);
});

renderMarkers(window.__INITIAL_PROJECTS__ || []);
applySummary(window.__INITIAL_SUMMARY__ || {});
setInterval(refreshSummary, 15000);
setInterval(refreshProjects, 30000);
