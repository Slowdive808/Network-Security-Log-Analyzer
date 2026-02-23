import { useEffect, useRef, useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { getStats } from "../api/client";

function useCountUp(target, duration = 1400) {
  const [count, setCount] = useState(0);
  const rafRef = useRef(null);
  useEffect(() => {
    if (!target) { setCount(0); return; }
    let startTime = null;
    const tick = (now) => {
      if (!startTime) startTime = now;
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 4);
      setCount(Math.floor(eased * target));
      if (progress < 1) rafRef.current = requestAnimationFrame(tick);
      else setCount(target);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration]);
  return count;
}

const TYPE_COLORS = { brute_force: "#ef4444", port_scan: "#a855f7", traffic_spike: "#f59e0b", off_hours: "#06b6d4" };
const SEV_COLORS  = { critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#22c55e" };
const ACCENTS = ["#06b6d4", "#3b82f6", "#f59e0b", "#ef4444", "#a855f7", "#22c55e"];

const TT = {
  contentStyle: { background: "rgba(6,20,45,0.95)", border: "1px solid rgba(6,182,212,0.3)", borderRadius: 8, fontSize: 12 },
  labelStyle: { color: "#64748b" },
  cursor: { fill: "rgba(6,182,212,0.04)" },
};

function StatCard({ label, value, icon, accent, sub, delay }) {
  const isNum = typeof value === "number";
  const display = useCountUp(isNum ? value : 0);
  return (
    <div className={`stat-card anim-up ${delay}`} style={{ flex: 1, minWidth: 160, borderLeftColor: accent, boxShadow: `0 0 28px ${accent}15` }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div className="stat-number" style={{ color: accent }}>
            {isNum ? display.toLocaleString() : value}
          </div>
          <div className="stat-label">{label}</div>
          {sub && <div style={{ fontSize: 10, color: "#475569", marginTop: 6 }}>{sub}</div>}
        </div>
        <div style={{ fontSize: 24, opacity: 0.18, filter: `drop-shadow(0 0 8px ${accent})`, marginTop: 2 }}>{icon}</div>
      </div>
    </div>
  );
}

function ChartCard({ title, children, delay }) {
  return (
    <div className={`card anim-up ${delay}`} style={{ padding: "20px 22px" }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", color: "#475569", textTransform: "uppercase", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 3, height: 14, borderRadius: 2, background: "#06b6d4", boxShadow: "0 0 6px #06b6d4" }} />
        {title}
      </div>
      {children}
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => { getStats().then(setStats).catch((e) => setError(e.message)); }, []);

  if (error) return <div className="anim-up" style={{ color: "#f87171", padding: "40px 0", fontSize: 13 }}>✗ {error}</div>;
  if (!stats) return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, paddingTop: 20 }}>
      {[...Array(4)].map((_, i) => (
        <div key={i} style={{ height: 100, borderRadius: 10, background: "linear-gradient(90deg, rgba(6,20,45,0.6) 25%, rgba(6,182,212,0.04) 50%, rgba(6,20,45,0.6) 75%)", backgroundSize: "200% 100%", animation: "shimmer 1.6s infinite" }} />
      ))}
    </div>
  );

  const pieData = Object.entries(stats.anomalies_by_type).map(([name, value]) => ({ name: name.replace(/_/g, " "), value, key: name }));
  const sevData = ["critical", "high", "medium", "low"].map((s) => ({ name: s.charAt(0).toUpperCase() + s.slice(1), value: stats.anomalies_by_severity[s] || 0 }));

  return (
    <div>
      <div className="anim-up" style={{ marginBottom: 32 }}>
        <h1 className="page-title">Security Dashboard</h1>
        <p className="page-sub">Aggregated analysis across all ingested log files</p>
      </div>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 20 }}>
        <StatCard label="Log Files"     value={stats.total_files}    icon="◎"  accent="#3b82f6" delay="d1" />
        <StatCard label="Total Events"  value={stats.total_events}   icon="≋"  accent="#6366f1" delay="d2" />
        <StatCard label="Anomalies"     value={stats.total_anomalies} icon="⚡" accent="#f59e0b" delay="d3" />
        <StatCard label="High / Critical" value={stats.high_severity_anomalies} icon="⚠"
          accent={stats.high_severity_anomalies > 0 ? "#ef4444" : "#22c55e"}
          sub={stats.high_severity_anomalies > 0 ? "Requires attention" : "All clear"}
          delay="d4" />
      </div>

      <ChartCard title="Events Over Time" delay="d5">
        <ResponsiveContainer width="100%" height={215}>
          <AreaChart data={stats.events_over_time}>
            <defs>
              <linearGradient id="evGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#06b6d4" stopOpacity={0.28} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,130,246,0.1)" />
            <XAxis dataKey="date" stroke="#1e3a5f" tick={{ fill: "#475569", fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis stroke="#1e3a5f" tick={{ fill: "#475569", fontSize: 10 }} />
            <Tooltip {...TT} />
            <Area type="monotone" dataKey="count" name="Events" stroke="#06b6d4" fill="url(#evGrad)" strokeWidth={2} dot={false} activeDot={{ r: 5, fill: "#06b6d4", strokeWidth: 0 }} />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginTop: 14 }}>
        <ChartCard title="Activity by Hour" delay="d6">
          <ResponsiveContainer width="100%" height={185}>
            <BarChart data={stats.events_by_hour} barSize={9}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,130,246,0.1)" />
              <XAxis dataKey="hour" stroke="#1e3a5f" tick={{ fill: "#475569", fontSize: 9 }} />
              <YAxis stroke="#1e3a5f" tick={{ fill: "#475569", fontSize: 9 }} />
              <Tooltip {...TT} />
              <Bar dataKey="count" name="Events" radius={[3, 3, 0, 0]}>
                {stats.events_by_hour.map((e) => (
                  <Cell key={e.hour} fill={e.hour < 7 || e.hour >= 19 ? "#ef444480" : "#06b6d4"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Anomaly Types" delay="d7">
          {pieData.length === 0 ? (
            <div style={{ height: 185, display: "flex", alignItems: "center", justifyContent: "center", color: "#334155", fontSize: 12 }}>
              No anomalies detected yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={185}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={68} innerRadius={34} paddingAngle={3}
                  label={({ percent }) => `${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={10}>
                  {pieData.map((e) => <Cell key={e.key} fill={TYPE_COLORS[e.key] || "#64748b"} />)}
                </Pie>
                <Tooltip {...TT} />
                <Legend iconSize={8} iconType="circle" wrapperStyle={{ fontSize: 10, color: "#64748b" }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Severity Breakdown" delay="d8">
          <ResponsiveContainer width="100%" height={185}>
            <BarChart data={sevData} layout="vertical" barSize={14}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,130,246,0.1)" />
              <XAxis type="number" stroke="#1e3a5f" tick={{ fill: "#475569", fontSize: 9 }} />
              <YAxis type="category" dataKey="name" stroke="#1e3a5f" tick={{ fill: "#94a3b8", fontSize: 10 }} width={60} />
              <Tooltip {...TT} />
              <Bar dataKey="value" name="Count" radius={[0, 4, 4, 0]}>
                {sevData.map((e) => <Cell key={e.name} fill={SEV_COLORS[e.name.toLowerCase()] || "#64748b"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {stats.top_source_ips.length > 0 && (
        <div className="card anim-up d8" style={{ padding: "20px 24px", marginTop: 14 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", color: "#475569", textTransform: "uppercase", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 3, height: 14, borderRadius: 2, background: "#06b6d4", boxShadow: "0 0 6px #06b6d4" }} />
            Top Source IPs
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 48px" }}>
            {stats.top_source_ips.map((item, i) => {
              const pct = (item.count / stats.top_source_ips[0].count) * 100;
              const accent = ACCENTS[i % ACCENTS.length];
              return (
                <div key={item.ip} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 10, color: "#334155", width: 14, textAlign: "right", flexShrink: 0 }}>{i + 1}</span>
                  <span style={{ fontSize: 11, color: "#94a3b8", width: 118, flexShrink: 0, fontFamily: "monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.ip}</span>
                  <div style={{ flex: 1, background: "rgba(6,182,212,0.07)", borderRadius: 4, height: 6, overflow: "hidden" }}>
                    <div style={{ width: `${pct}%`, height: "100%", background: accent, borderRadius: 4, boxShadow: `0 0 6px ${accent}80` }} />
                  </div>
                  <span style={{ fontSize: 10, color: "#475569", width: 44, textAlign: "right", flexShrink: 0 }}>{item.count.toLocaleString()}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
