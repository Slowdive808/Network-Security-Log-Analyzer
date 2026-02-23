import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { listAnomalies, listFiles, getFileAnomalies } from "../api/client";
import AnomalyCard from "../components/AnomalyCard";

export default function Anomalies() {
  const [searchParams] = useSearchParams();
  const [anomalies, setAnomalies] = useState([]);
  const [files, setFiles] = useState([]);
  const [fileId, setFileId] = useState(searchParams.get("file") || "");
  const [filters, setFilters] = useState({ severity: "", anomaly_type: "", false_positive: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listFiles().then((fs) => setFiles(fs.filter((f) => f.status === "done")));
  }, []);

  const load = () => {
    setLoading(true);
    const p = {};
    if (filters.severity) p.severity = filters.severity;
    if (filters.anomaly_type) p.anomaly_type = filters.anomaly_type;
    if (filters.false_positive !== "") p.false_positive = filters.false_positive === "true";

    const fetch = fileId ? getFileAnomalies(fileId) : listAnomalies(p);
    fetch
      .then((data) => {
        let filtered = data;
        if (fileId && filters.severity) filtered = filtered.filter((a) => a.severity === filters.severity);
        if (fileId && filters.anomaly_type) filtered = filtered.filter((a) => a.anomaly_type === filters.anomaly_type);
        if (fileId && filters.false_positive !== "") {
          const fp = filters.false_positive === "true";
          filtered = filtered.filter((a) => a.false_positive === fp);
        }
        setAnomalies(filtered);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(load, [fileId, filters]);

  const handleUpdate = (updated) =>
    setAnomalies((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));

  const counts = {
    critical: anomalies.filter((a) => a.severity === "critical" && !a.false_positive).length,
    high:     anomalies.filter((a) => a.severity === "high"     && !a.false_positive).length,
    medium:   anomalies.filter((a) => a.severity === "medium"   && !a.false_positive).length,
    low:      anomalies.filter((a) => a.severity === "low"      && !a.false_positive).length,
    fp:       anomalies.filter((a) => a.false_positive).length,
  };

  return (
    <div>
      <div className="anim-up" style={{ marginBottom: 32 }}>
        <h1 className="page-title">Anomalies</h1>
        <p className="page-sub">Detected security events. Click "Mark FP" to dismiss false positives.</p>
      </div>

      {/* Filter bar */}
      <div className="card anim-up d1" style={{
        padding: "14px 18px", marginBottom: 20,
        display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center",
      }}>
        <select className="select" value={fileId} onChange={(e) => setFileId(e.target.value)} style={{ minWidth: 180 }}>
          <option value="">All files</option>
          {files.map((f) => <option key={f.id} value={f.id}>{f.original_name}</option>)}
        </select>

        <select className="select" value={filters.severity} onChange={(e) => setFilters((p) => ({ ...p, severity: e.target.value }))}>
          <option value="">All severities</option>
          {["critical", "high", "medium", "low"].map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>

        <select className="select" value={filters.anomaly_type} onChange={(e) => setFilters((p) => ({ ...p, anomaly_type: e.target.value }))}>
          <option value="">All types</option>
          <option value="brute_force">Brute Force</option>
          <option value="port_scan">Port Scan</option>
          <option value="traffic_spike">Traffic Spike</option>
          <option value="off_hours">Off-Hours</option>
        </select>

        <select className="select" value={filters.false_positive} onChange={(e) => setFilters((p) => ({ ...p, false_positive: e.target.value }))}>
          <option value="">Active + FP</option>
          <option value="false">Active only</option>
          <option value="true">False positives</option>
        </select>

        {/* Severity counters */}
        <div style={{ marginLeft: "auto", display: "flex", gap: 16, flexWrap: "wrap" }}>
          {[
            { label: "CRITICAL", count: counts.critical, color: "#ef4444" },
            { label: "HIGH",     count: counts.high,     color: "#f97316" },
            { label: "MEDIUM",   count: counts.medium,   color: "#f59e0b" },
            { label: "LOW",      count: counts.low,      color: "#22c55e" },
          ].map(({ label, count, color }) => (
            <span key={label} style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", color: count > 0 ? color : "#334155" }}>
              {count} {label}
            </span>
          ))}
          {counts.fp > 0 && (
            <span style={{ fontSize: 10, color: "#334155", letterSpacing: "0.08em" }}>{counts.fp} FP</span>
          )}
        </div>
      </div>

      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {[...Array(4)].map((_, i) => (
            <div key={i} style={{
              height: 110, borderRadius: 10,
              background: "linear-gradient(90deg, rgba(6,20,45,0.6) 25%, rgba(6,182,212,0.03) 50%, rgba(6,20,45,0.6) 75%)",
              backgroundSize: "200% 100%",
              animation: `shimmer 1.4s ${i * 0.07}s infinite`,
            }} />
          ))}
        </div>
      )}

      {!loading && anomalies.length === 0 && (
        <div className="card anim-up" style={{ padding: "60px 40px", textAlign: "center" }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.2em", color: "#1e3a5f", marginBottom: 16 }}>NO ANOMALIES</div>
          <div style={{ color: "#334155", fontSize: 13 }}>
            {fileId ? "No anomalies detected in this file." : "Upload and analyse a log file to see anomalies here."}
          </div>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {anomalies.map((a, i) => (
          <AnomalyCard key={a.id} anomaly={a} onUpdate={handleUpdate} index={i} />
        ))}
      </div>
    </div>
  );
}
