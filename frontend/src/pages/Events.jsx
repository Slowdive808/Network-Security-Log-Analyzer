import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { listFiles, getFileEvents } from "../api/client";

const STATUS_COLOR = { success: "#22c55e", failed: "#ef4444", error: "#f97316", unknown: "#475569" };

const PAGE_SIZE = 100;

export default function Events() {
  const [searchParams] = useSearchParams();
  const [files, setFiles] = useState([]);
  const [fileId, setFileId] = useState(searchParams.get("file") || "");
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({ status: "", event_type: "", source_ip: "", username: "" });
  const [page, setPage] = useState(0);

  useEffect(() => {
    listFiles().then((fs) => setFiles(fs.filter((f) => f.status === "done")));
  }, []);

  useEffect(() => {
    if (!fileId) return;
    setLoading(true);
    const params = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
    Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });
    getFileEvents(fileId, params)
      .then(setEvents)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [fileId, filters, page]);

  const setFilter = (key, val) => { setFilters((p) => ({ ...p, [key]: val })); setPage(0); };

  return (
    <div>
      <div className="anim-up" style={{ marginBottom: 32 }}>
        <h1 className="page-title">Events</h1>
        <p className="page-sub">Browse and filter all parsed log events across files.</p>
      </div>

      {/* Filter bar */}
      <div className="anim-up d1 card" style={{
        padding: "14px 18px", marginBottom: 20,
        display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center",
      }}>
        <select className="select" value={fileId} onChange={(e) => { setFileId(e.target.value); setPage(0); }} style={{ minWidth: 180 }}>
          <option value="">— Select log file —</option>
          {files.map((f) => (
            <option key={f.id} value={f.id}>{f.original_name}</option>
          ))}
        </select>

        <select className="select" value={filters.status} onChange={(e) => setFilter("status", e.target.value)}>
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
          <option value="error">Error</option>
        </select>

        <select className="select" value={filters.event_type} onChange={(e) => setFilter("event_type", e.target.value)}>
          <option value="">All types</option>
          <option value="auth">Auth</option>
          <option value="network">Network</option>
          <option value="system">System</option>
        </select>

        <input
          className="input"
          placeholder="Source IP…"
          value={filters.source_ip}
          onChange={(e) => setFilter("source_ip", e.target.value)}
          style={{ width: 150 }}
        />
        <input
          className="input"
          placeholder="Username…"
          value={filters.username}
          onChange={(e) => setFilter("username", e.target.value)}
          style={{ width: 140 }}
        />

        {events.length > 0 && (
          <span style={{ fontSize: 10, color: "#334155", marginLeft: "auto", letterSpacing: "0.06em" }}>
            {events.length} events · page {page + 1}
          </span>
        )}
      </div>

      {/* Empty / loading states */}
      {!fileId && (
        <div className="card anim-up d2" style={{ padding: "60px 40px", textAlign: "center" }}>
          <div style={{ fontSize: 40, marginBottom: 16, opacity: 0.2 }}>≡</div>
          <div style={{ color: "#334155", fontSize: 13 }}>Select a file above to browse its events.</div>
        </div>
      )}

      {fileId && loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {[...Array(8)].map((_, i) => (
            <div key={i} style={{
              height: 36, borderRadius: 6,
              background: "linear-gradient(90deg, rgba(6,20,45,0.6) 25%, rgba(6,182,212,0.03) 50%, rgba(6,20,45,0.6) 75%)",
              backgroundSize: "200% 100%",
              animation: `shimmer 1.4s ${i * 0.05}s infinite`,
            }} />
          ))}
        </div>
      )}

      {fileId && !loading && events.length === 0 && (
        <div className="card anim-up" style={{ padding: "40px", textAlign: "center", color: "#334155", fontSize: 13 }}>
          No events match the current filters.
        </div>
      )}

      {events.length > 0 && (
        <>
          <div className="card anim-up d2" style={{ overflow: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  {["Timestamp", "Source IP", "User", "Type", "Action", "Status", "Port", "Proto", "Bytes Sent"].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.id}>
                    <td style={{ color: "#334155", fontFamily: "monospace", fontSize: 11, whiteSpace: "nowrap" }}>
                      {e.timestamp ? new Date(e.timestamp).toLocaleString() : "—"}
                    </td>
                    <td style={{ fontFamily: "monospace", color: "#93c5fd", whiteSpace: "nowrap" }}>{e.source_ip || "—"}</td>
                    <td style={{ color: "#c4b5fd" }}>{e.username || "—"}</td>
                    <td style={{ color: "#64748b" }}>{e.event_type || "—"}</td>
                    <td style={{ color: "#94a3b8" }}>{e.action || "—"}</td>
                    <td>
                      <span style={{
                        fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
                        color: STATUS_COLOR[e.status] || "#475569",
                        background: `${STATUS_COLOR[e.status] || "#475569"}15`,
                        padding: "2px 8px", borderRadius: 20, whiteSpace: "nowrap",
                      }}>
                        {(e.status || "—").toUpperCase()}
                      </span>
                    </td>
                    <td style={{ color: "#475569" }}>{e.port ?? "—"}</td>
                    <td style={{ color: "#475569" }}>{e.protocol || "—"}</td>
                    <td style={{ color: "#475569", textAlign: "right" }}>
                      {e.bytes_sent != null ? e.bytes_sent.toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div style={{ display: "flex", gap: 10, marginTop: 14, justifyContent: "center", alignItems: "center" }}>
            <button
              className="btn btn-ghost"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              ← Prev
            </button>
            <span style={{ fontSize: 11, color: "#334155", padding: "0 10px" }}>Page {page + 1}</span>
            <button
              className="btn btn-ghost"
              disabled={events.length < PAGE_SIZE}
              onClick={() => setPage((p) => p + 1)}
            >
              Next →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
