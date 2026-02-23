import { useState } from "react";
import { updateAnomaly } from "../api/client";

const SEV = {
  critical: { border: "#ef4444", glow: "rgba(239,68,68,0.15)",  text: "#fca5a5", label: "rgba(239,68,68,0.15)",  labelBorder: "rgba(239,68,68,0.4)" },
  high:     { border: "#f97316", glow: "rgba(249,115,22,0.12)", text: "#fdba74", label: "rgba(249,115,22,0.12)", labelBorder: "rgba(249,115,22,0.4)" },
  medium:   { border: "#f59e0b", glow: "rgba(245,158,11,0.12)", text: "#fcd34d", label: "rgba(245,158,11,0.12)", labelBorder: "rgba(245,158,11,0.4)" },
  low:      { border: "#22c55e", glow: "rgba(34,197,94,0.10)",  text: "#86efac", label: "rgba(34,197,94,0.10)",  labelBorder: "rgba(34,197,94,0.4)" },
};

const TYPE_ABBR = { brute_force: "BF", port_scan: "PS", traffic_spike: "TS", off_hours: "OH" };
const TYPE_COLOR = { brute_force: "#ef4444", port_scan: "#a855f7", traffic_spike: "#f59e0b", off_hours: "#06b6d4" };

function fmt(dt) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function AnomalyCard({ anomaly, onUpdate, index = 0 }) {
  const s = SEV[anomaly.severity] || SEV.low;
  const [toggling, setToggling] = useState(false);
  const [hovered, setHovered] = useState(false);

  const toggleFP = async (e) => {
    e.stopPropagation();
    setToggling(true);
    try {
      const updated = await updateAnomaly(anomaly.id, { false_positive: !anomaly.false_positive });
      onUpdate?.(updated);
    } finally {
      setToggling(false);
    }
  };

  const isFP = anomaly.false_positive;

  return (
    <div
      className={`anim-up d${Math.min(index + 1, 8)}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: isFP ? "rgba(6,20,45,0.35)" : `rgba(6,20,45,0.75)`,
        border: `1px solid ${isFP ? "rgba(59,130,246,0.1)" : s.border}40`,
        borderLeft: `3px solid ${isFP ? "#1e3a5f" : s.border}`,
        borderRadius: 10,
        padding: "16px 20px",
        opacity: isFP ? 0.45 : 1,
        transform: hovered && !isFP ? "translateY(-3px)" : "translateY(0)",
        boxShadow: hovered && !isFP ? `0 10px 36px ${s.glow}, 0 0 0 1px ${s.border}30` : "none",
        transition: "all 0.22s ease",
        backdropFilter: "blur(12px)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Subtle inner glow on hover */}
      {hovered && !isFP && (
        <div style={{
          position: "absolute", inset: 0, pointerEvents: "none",
          background: `radial-gradient(ellipse at top left, ${s.glow}, transparent 70%)`,
          borderRadius: 10,
        }} />
      )}

      {/* Header row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10, position: "relative" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Type icon */}
          <div style={{
            width: 36, height: 36, borderRadius: 8, flexShrink: 0,
            background: `${TYPE_COLOR[anomaly.anomaly_type] || "#64748b"}18`,
            border: `1px solid ${TYPE_COLOR[anomaly.anomaly_type] || "#64748b"}35`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 10, fontWeight: 700, letterSpacing: "0.06em",
            color: TYPE_COLOR[anomaly.anomaly_type] || "#64748b",
          }}>
            {TYPE_ABBR[anomaly.anomaly_type] || "??"}
          </div>

          <div>
            {/* Severity badge */}
            <span style={{
              fontSize: 10, fontWeight: 700, letterSpacing: "0.1em",
              background: s.label, border: `1px solid ${s.labelBorder}`,
              color: s.text, padding: "2px 10px", borderRadius: 20,
              marginRight: 8,
              animation: "pulseGlow 2.5s ease-in-out infinite",
            }}>
              {anomaly.severity.toUpperCase()}
            </span>
            <span style={{
              fontSize: 10, color: TYPE_COLOR[anomaly.anomaly_type] || "#64748b",
              letterSpacing: "0.08em", fontWeight: 600,
            }}>
              {anomaly.anomaly_type.replace(/_/g, " ").toUpperCase()}
            </span>
          </div>
        </div>

        {/* False-positive toggle */}
        <button
          onClick={toggleFP}
          disabled={toggling}
          style={{
            fontSize: 10, cursor: toggling ? "wait" : "pointer",
            background: "transparent",
            border: `1px solid ${isFP ? "rgba(34,197,94,0.3)" : "rgba(59,130,246,0.2)"}`,
            color: isFP ? "#22c55e" : "#475569",
            padding: "4px 12px", borderRadius: 20,
            fontFamily: "inherit", fontWeight: 600, letterSpacing: "0.06em",
            transition: "all 0.15s",
          }}
        >
          {isFP ? "↩ Restore" : "Mark FP"}
        </button>
      </div>

      {/* Description */}
      <div style={{
        fontSize: 13, color: s.text, marginBottom: 12,
        lineHeight: 1.55, fontWeight: 500, position: "relative",
      }}>
        {anomaly.description}
      </div>

      {/* Meta pills */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 12px", position: "relative" }}>
        {anomaly.source_ip && (
          <Pill label="IP" value={anomaly.source_ip} mono />
        )}
        {anomaly.username && (
          <Pill label="User" value={anomaly.username} />
        )}
        {anomaly.event_count != null && (
          <Pill label="Events" value={anomaly.event_count} />
        )}
        {anomaly.score != null && (
          <Pill label="Score" value={`${anomaly.score}/100`} accent={s.text} />
        )}
        {anomaly.start_time && (
          <Pill label="At" value={fmt(anomaly.start_time)} />
        )}
        {isFP && (
          <span style={{ fontSize: 10, color: "#f59e0b", alignSelf: "center", letterSpacing: "0.06em" }}>
            ⚑ false positive
          </span>
        )}
      </div>
    </div>
  );
}

function Pill({ label, value, mono, accent }) {
  return (
    <span style={{
      fontSize: 10, color: accent || "#64748b",
      background: "rgba(59,130,246,0.07)",
      border: "1px solid rgba(59,130,246,0.12)",
      borderRadius: 20, padding: "3px 10px",
      fontFamily: mono ? "monospace" : "inherit",
    }}>
      <span style={{ color: "#334155", marginRight: 4 }}>{label}:</span>
      {value}
    </span>
  );
}
