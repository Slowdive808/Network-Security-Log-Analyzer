import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import FileUpload from "../components/FileUpload";
import { listFiles, deleteFile, getFile } from "../api/client";

const STATUS_CONFIG = {
  done:       { color: "#22c55e", label: "DONE",       glow: "rgba(34,197,94,0.2)" },
  processing: { color: "#f59e0b", label: "PROCESSING", glow: "rgba(245,158,11,0.2)" },
  pending:    { color: "#475569", label: "PENDING",    glow: "none" },
  error:      { color: "#ef4444", label: "ERROR",      glow: "rgba(239,68,68,0.2)" },
};

function FileRow({ file, onDelete, onClick, index }) {
  const [current, setCurrent] = useState(file);

  useEffect(() => {
    if (current.status !== "processing" && current.status !== "pending") return;
    const id = setInterval(async () => {
      const updated = await getFile(current.id).catch(() => null);
      if (updated) setCurrent(updated);
      if (updated?.status === "done" || updated?.status === "error") clearInterval(id);
    }, 1500);
    return () => clearInterval(id);
  }, [current.id, current.status]);

  const cfg = STATUS_CONFIG[current.status] || STATUS_CONFIG.pending;
  const sizeKB = (current.file_size / 1024).toFixed(1);

  return (
    <div
      className={`card anim-up d${Math.min(index + 2, 8)}`}
      onClick={() => onClick(current)}
      style={{
        padding: "14px 20px",
        display: "flex", alignItems: "center", gap: 16,
        cursor: current.status === "done" ? "pointer" : "default",
      }}
    >
      {/* File type icon */}
      <div style={{
        width: 40, height: 40, borderRadius: 8, flexShrink: 0,
        background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.2)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 18, color: "#3b82f6",
      }}>
        {current.original_name?.endsWith(".json") ? "{ }" :
         current.original_name?.endsWith(".csv") ? "≡" : "≈"}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, color: "#e2e8f0", marginBottom: 3, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {current.original_name}
        </div>
        <div style={{ fontSize: 11, color: "#475569" }}>
          {sizeKB} KB
          {current.file_format && <span style={{ marginLeft: 8, color: "#334155" }}>· {current.file_format.toUpperCase()}</span>}
          <span style={{ marginLeft: 8 }}>· {new Date(current.upload_time).toLocaleString()}</span>
        </div>
      </div>

      {/* Stats */}
      {current.status === "done" && (
        <div style={{ display: "flex", gap: 20, flexShrink: 0 }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#3b82f6" }}>{current.event_count?.toLocaleString()}</div>
            <div style={{ fontSize: 10, color: "#334155", letterSpacing: "0.06em" }}>EVENTS</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: current.anomaly_count > 0 ? "#f59e0b" : "#22c55e" }}>
              {current.anomaly_count}
            </div>
            <div style={{ fontSize: 10, color: "#334155", letterSpacing: "0.06em" }}>ANOMALIES</div>
          </div>
        </div>
      )}

      {/* Status badge */}
      <div style={{
        flexShrink: 0, padding: "4px 14px",
        background: `${cfg.glow}`,
        border: `1px solid ${cfg.color}40`,
        borderRadius: 20, fontSize: 10, fontWeight: 700,
        color: cfg.color, letterSpacing: "0.1em",
        animation: current.status === "processing" ? "pulseGlow 1.5s ease-in-out infinite" : undefined,
      }}>
        {cfg.label}
      </div>

      {current.status === "error" && (
        <div style={{ fontSize: 11, color: "#f87171", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={current.error_message}>
          {current.error_message}
        </div>
      )}

      <button
        onClick={(e) => { e.stopPropagation(); onDelete(current.id); }}
        style={{
          background: "transparent", border: "1px solid rgba(239,68,68,0.2)",
          color: "#475569", padding: "5px 12px", borderRadius: 6,
          cursor: "pointer", fontSize: 11, fontFamily: "inherit",
          transition: "all 0.15s",
          flexShrink: 0,
        }}
        onMouseEnter={(e) => { e.currentTarget.style.color = "#ef4444"; e.currentTarget.style.borderColor = "rgba(239,68,68,0.5)"; }}
        onMouseLeave={(e) => { e.currentTarget.style.color = "#475569"; e.currentTarget.style.borderColor = "rgba(239,68,68,0.2)"; }}
      >
        ✕
      </button>
    </div>
  );
}

export default function Upload() {
  const [files, setFiles] = useState([]);
  const navigate = useNavigate();

  useEffect(() => { listFiles().then(setFiles).catch(console.error); }, []);

  const handleUploaded = (newFile) => setFiles((prev) => [newFile, ...prev]);

  const handleDelete = async (id) => {
    if (!confirm("Delete this file and all its data?")) return;
    await deleteFile(id);
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleClick = (file) => {
    if (file.status === "done") navigate(`/anomalies?file=${file.id}`);
  };

  return (
    <div style={{ maxWidth: 820, margin: "0 auto" }}>
      <div className="anim-up" style={{ marginBottom: 32 }}>
        <h1 className="page-title">Upload Log File</h1>
        <p className="page-sub">Drop a log file to parse and analyse it. Results appear in Events and Anomalies.</p>
      </div>

      {/* Drop zone */}
      <div className="anim-up d1">
        <FileUpload onUploaded={handleUploaded} />
      </div>

      {/* Hint */}
      <div className="anim-up d2" style={{
        marginTop: 12, padding: "10px 16px",
        background: "rgba(59,130,246,0.05)", borderRadius: 6,
        border: "1px solid rgba(59,130,246,0.1)",
        fontSize: 11, color: "#334155",
      }}>
        <span style={{ color: "#475569" }}>Tip:</span> Run{" "}
        <code style={{ color: "#06b6d4", background: "rgba(6,182,212,0.1)", padding: "1px 6px", borderRadius: 3 }}>
          python backend/generate_sample_data.py
        </code>{" "}
        to create synthetic logs with injected attack patterns.
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div style={{ marginTop: 36 }}>
          <div className="anim-up d3" style={{
            fontSize: 10, fontWeight: 700, letterSpacing: "0.12em",
            color: "#334155", textTransform: "uppercase", marginBottom: 12,
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <div style={{ width: 3, height: 14, borderRadius: 2, background: "#06b6d4", boxShadow: "0 0 6px #06b6d4" }} />
            Uploaded Files ({files.length})
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {files.map((f, i) => (
              <FileRow key={f.id} file={f} onDelete={handleDelete} onClick={handleClick} index={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
