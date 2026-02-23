import { useRef, useState } from "react";
import { uploadFile } from "../api/client";

export default function FileUpload({ onUploaded }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const handleFile = async (file) => {
    if (!file) return;
    setError(null);
    setUploading(true);
    setProgress(10);

    // Fake progress ticks while waiting
    const ticker = setInterval(() => setProgress((p) => Math.min(p + 8, 88)), 300);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const result = await uploadFile(fd);
      clearInterval(ticker);
      setProgress(100);
      setTimeout(() => { setUploading(false); setProgress(0); }, 600);
      onUploaded?.(result);
    } catch (e) {
      clearInterval(ticker);
      setError(e.message);
      setUploading(false);
      setProgress(0);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  return (
    <div>
      <div
        onClick={() => !uploading && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{
          borderRadius: 12,
          padding: "52px 40px",
          textAlign: "center",
          cursor: uploading ? "wait" : "pointer",
          position: "relative",
          overflow: "hidden",
          transition: "all 0.25s ease",
          background: dragging
            ? "rgba(6,182,212,0.08)"
            : "rgba(6,20,45,0.6)",
          border: `2px dashed ${dragging ? "rgba(6,182,212,0.6)" : "rgba(59,130,246,0.2)"}`,
          boxShadow: dragging ? "0 0 40px rgba(6,182,212,0.12), inset 0 0 40px rgba(6,182,212,0.04)" : "none",
        }}
      >
        {/* Progress bar */}
        {uploading && (
          <div style={{
            position: "absolute", top: 0, left: 0, height: 2,
            background: "linear-gradient(90deg, #3b82f6, #06b6d4)",
            width: `${progress}%`,
            transition: "width 0.3s ease",
            boxShadow: "0 0 8px #06b6d4",
          }} />
        )}

        {/* Animated ring when dragging */}
        {dragging && (
          <div style={{
            position: "absolute", inset: 0, borderRadius: 12,
            background: "radial-gradient(circle at center, rgba(6,182,212,0.06), transparent 70%)",
            pointerEvents: "none",
          }} />
        )}

        <div style={{ fontSize: 48, marginBottom: 16, lineHeight: 1 }}>
          {uploading ? "⏳" : dragging ? "📂" : "⬆"}
        </div>
        <div style={{ fontSize: 15, fontWeight: 600, color: dragging ? "#06b6d4" : "#94a3b8", marginBottom: 8, transition: "color 0.2s" }}>
          {uploading ? `Uploading… ${progress}%` :
           dragging ? "Drop to upload" :
           "Drop a log file here or click to browse"}
        </div>
        <div style={{ fontSize: 11, color: "#334155", letterSpacing: "0.06em" }}>
          Supported: .csv · .json · .log · .syslog · .auth · .txt
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.json,.log,.syslog,.auth,.txt"
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files[0])}
        />
      </div>

      {error && (
        <div style={{
          marginTop: 10, padding: "10px 16px",
          background: "rgba(239,68,68,0.08)",
          border: "1px solid rgba(239,68,68,0.3)",
          borderRadius: 6, color: "#f87171", fontSize: 12,
        }}>
          ✗ {error}
        </div>
      )}
    </div>
  );
}
