import { useEffect, useState } from "react";
import { listFiles, listReports, createReport, reportDownloadUrl } from "../api/client";

export default function Reports() {
  const [files, setFiles] = useState([]);
  const [fileId, setFileId] = useState("");
  const [reports, setReports] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [reportType, setReportType] = useState("summary");
  const [fmt, setFmt] = useState("pdf");
  const [error, setError] = useState(null);

  useEffect(() => {
    listFiles().then((fs) => setFiles(fs.filter((f) => f.status === "done")));
  }, []);

  useEffect(() => {
    if (!fileId) { setReports([]); return; }
    listReports(fileId).then(setReports).catch(console.error);
  }, [fileId]);

  const generate = async () => {
    if (!fileId) return;
    setGenerating(true);
    setError(null);
    try {
      const rep = await createReport(fileId, reportType, fmt);
      setReports((prev) => [rep, ...prev]);
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div style={{ maxWidth: 780, margin: "0 auto" }}>
      <div className="anim-up" style={{ marginBottom: 32 }}>
        <h1 className="page-title">Reports</h1>
        <p className="page-sub">Generate PDF or PNG summary reports from analysed log files.</p>
      </div>

      {/* Generator panel */}
      <div className="card anim-up d1" style={{ padding: "24px 26px", marginBottom: 28 }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", color: "#475569", textTransform: "uppercase", marginBottom: 18, display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 3, height: 14, borderRadius: 2, background: "#06b6d4", boxShadow: "0 0 6px #06b6d4" }} />
          Generate New Report
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end" }}>
          <div>
            <label style={{ display: "block", fontSize: 10, color: "#334155", letterSpacing: "0.08em", marginBottom: 6, textTransform: "uppercase" }}>Log File</label>
            <select className="select" value={fileId} onChange={(e) => setFileId(e.target.value)} style={{ minWidth: 200 }}>
              <option value="">— Select file —</option>
              {files.map((f) => <option key={f.id} value={f.id}>{f.original_name}</option>)}
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: 10, color: "#334155", letterSpacing: "0.08em", marginBottom: 6, textTransform: "uppercase" }}>Report Type</label>
            <select className="select" value={reportType} onChange={(e) => setReportType(e.target.value)}>
              <option value="summary">Summary (1 page)</option>
              <option value="detailed">Detailed (3 pages)</option>
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: 10, color: "#334155", letterSpacing: "0.08em", marginBottom: 6, textTransform: "uppercase" }}>Format</label>
            <select className="select" value={fmt} onChange={(e) => setFmt(e.target.value)}>
              <option value="pdf">PDF</option>
              <option value="png">PNG</option>
            </select>
          </div>
          <button
            className={`btn btn-primary`}
            onClick={generate}
            disabled={!fileId || generating}
          >
            {generating ? "⏳ Generating…" : "◉ Generate Report"}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: 12, color: "#f87171", fontSize: 12 }}>✗ {error}</div>
        )}
      </div>

      {fileId && !generating && reports.length === 0 && (
        <div className="card anim-up" style={{ padding: "40px", textAlign: "center", color: "#334155", fontSize: 13 }}>
          No reports generated for this file yet.
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {reports.map((rep, i) => (
          <div key={rep.id} className={`card anim-up d${Math.min(i + 2, 8)}`} style={{ padding: "16px 20px", display: "flex", alignItems: "center", gap: 16 }}>
            {/* Icon */}
            <div style={{
              width: 44, height: 44, borderRadius: 10, flexShrink: 0,
              background: rep.format === "pdf" ? "rgba(239,68,68,0.1)" : "rgba(59,130,246,0.1)",
              border: `1px solid ${rep.format === "pdf" ? "rgba(239,68,68,0.25)" : "rgba(59,130,246,0.25)"}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 22,
            }}>
              {rep.format === "pdf" ? "📄" : "🖼"}
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, color: "#e2e8f0", marginBottom: 4, fontWeight: 500 }}>
                {rep.report_type.charAt(0).toUpperCase() + rep.report_type.slice(1)} Report
                <span style={{
                  marginLeft: 8, fontSize: 10, fontWeight: 700,
                  background: "rgba(59,130,246,0.1)",
                  border: "1px solid rgba(59,130,246,0.2)",
                  color: "#3b82f6", padding: "2px 8px", borderRadius: 20,
                  letterSpacing: "0.08em",
                }}>
                  {rep.format.toUpperCase()}
                </span>
              </div>
              <div style={{ fontSize: 11, color: "#334155" }}>
                {new Date(rep.created_at).toLocaleString()}
              </div>
            </div>

            <a
              href={reportDownloadUrl(rep.file_id, rep.id)}
              target="_blank"
              rel="noreferrer"
              className="btn btn-primary"
              style={{ textDecoration: "none", flexShrink: 0 }}
            >
              ⬇ Download
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
