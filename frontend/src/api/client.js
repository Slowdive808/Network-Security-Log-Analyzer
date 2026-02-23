const BASE = "/api";

async function request(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Files ────────────────────────────────────────────────────────────────────

export function listFiles() {
  return request("/files");
}

export function getFile(id) {
  return request(`/files/${id}`);
}

export function uploadFile(formData) {
  return request("/files/upload", { method: "POST", body: formData });
}

export function deleteFile(id) {
  return request(`/files/${id}`, { method: "DELETE" });
}

export function getFileEvents(id, params = {}) {
  const q = new URLSearchParams(params).toString();
  return request(`/files/${id}/events${q ? "?" + q : ""}`);
}

export function getFileAnomalies(id) {
  return request(`/files/${id}/anomalies`);
}

// ── Anomalies ─────────────────────────────────────────────────────────────────

export function listAnomalies(params = {}) {
  const q = new URLSearchParams(params).toString();
  return request(`/anomalies${q ? "?" + q : ""}`);
}

export function updateAnomaly(id, patch) {
  return request(`/anomalies/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
}

// ── Reports ───────────────────────────────────────────────────────────────────

export function createReport(fileId, type = "summary", fmt = "pdf") {
  return request(`/reports/${fileId}?report_type=${type}&fmt=${fmt}`, { method: "POST" });
}

export function listReports(fileId) {
  return request(`/reports/${fileId}`);
}

export function reportDownloadUrl(fileId, reportId) {
  return `${BASE}/reports/${fileId}/${reportId}/download`;
}

// ── Stats ─────────────────────────────────────────────────────────────────────

export function getStats() {
  return request("/stats");
}
