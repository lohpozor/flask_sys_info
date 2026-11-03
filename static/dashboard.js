const REFRESH_MS = 500;

let infoLoaded = false;

function percentStatus(percent) {
  if (percent >= 90) return "bad";
  if (percent >= 70) return "warn";
  return "ok";
}

function temperatureStatus(celsius) {
  if (celsius >= 85) return "bad";
  if (celsius >= 70) return "warn";
  return "ok";
}

function setText(id, text) {
  document.getElementById(id).textContent = text;
}

function formatSpeed(bytesPerSecond) {
  if (bytesPerSecond >= 1024 ** 2) {
    return `${(bytesPerSecond / 1024 ** 2).toFixed(1)} MB/s`;
  }
  return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`;
}

function formatUptime(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return days > 0 ? `${days}d ${hours}h ${minutes}m` : `${hours}h ${minutes}m`;
}

// null приходит, когда датчик недоступен (например, температура CPU на Windows)
function renderGauge(id, data) {
  const gauge = document.getElementById(id);
  const temp = gauge.querySelector(".gauge-temp");

  if (data.temperature === null) {
    temp.textContent = "N/A";
    delete temp.dataset.status;
  } else {
    temp.textContent = `${data.temperature}°C`;
    temp.dataset.status = temperatureStatus(data.temperature);
  }
  gauge.querySelector(".gauge-load").textContent = data.percent === null ? "N/A" : `${data.percent}%`;
}

function renderUsage(id, usage) {
  const row = document.getElementById(id);
  row.dataset.status = percentStatus(usage.percent);
  row.querySelector(".row-value").textContent =
    `${usage.used_gb} / ${usage.total_gb} GB · ${usage.percent}%`;
}

function createRow(label, value, status) {
  const row = document.createElement("li");
  row.className = "row";
  row.dataset.status = status;

  const dot = document.createElement("span");
  dot.className = "dot";
  const labelEl = document.createElement("span");
  labelEl.className = "row-label";
  labelEl.textContent = label;
  const valueEl = document.createElement("span");
  valueEl.className = "row-value";
  valueEl.textContent = value;

  row.append(dot, labelEl, valueEl);
  return row;
}

function renderInterfaces(interfaces) {
  const rows = interfaces.map((iface) => createRow(iface.name, iface.ip, iface.up ? "ok" : "bad"));
  document.getElementById("interfaces").replaceChildren(...rows);
}

function setConnection(isOnline) {
  document.getElementById("connection").dataset.status = isOnline ? "ok" : "bad";
  setText("connection-text", isOnline ? "Online" : "Нет связи");
}

// Имя ПК, версия и ОС не меняются, поэтому их запрашиваем один раз
async function loadInfo() {
  const response = await fetch("/api/info");
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const info = await response.json();
  setText("hostname", info.hostname);
  setText("version", `v${info.version}`);
  setText("os", info.os);
  infoLoaded = true;
}

async function refresh() {
  try {
    if (!infoLoaded) {
      await loadInfo();
    }

    const response = await fetch("/api/metrics");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const m = await response.json();

    renderGauge("cpu", m.cpu);
    renderGauge("gpu", m.gpu);

    setText("uptime", formatUptime(m.uptime_seconds));
    setText("processes", m.processes);
    renderUsage("memory", m.memory);
    renderUsage("disk", m.disk);

    setText("download", formatSpeed(m.network.download_bps));
    setText("upload", formatSpeed(m.network.upload_bps));
    setText("received", `${m.network.received_gb} GB`);
    setText("sent", `${m.network.sent_gb} GB`);
    renderInterfaces(m.network.interfaces);

    setConnection(true);
    setText("updated", new Date().toLocaleTimeString());
  } catch (error) {
    console.error("Не удалось получить метрики:", error);
    setConnection(false);
  } finally {
    // Следующий запрос планируем только после завершения текущего, чтобы они не накапливались
    setTimeout(refresh, REFRESH_MS);
  }
}

refresh();
