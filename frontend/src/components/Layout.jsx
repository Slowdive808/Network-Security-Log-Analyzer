import { NavLink, Outlet } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/",          label: "Dashboard",  icon: "◈" },
  { to: "/upload",    label: "Upload",     icon: "⬆" },
  { to: "/events",    label: "Events",     icon: "≡" },
  { to: "/anomalies", label: "Anomalies",  icon: "⚠" },
  { to: "/reports",   label: "Reports",    icon: "◉" },
];

function Background() {
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none", overflow: "hidden" }}>
      <div style={{ position: "absolute", inset: 0, background: "#020b18" }} />

      {/* Moving grid overlay */}
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage:
          "linear-gradient(rgba(6,182,212,0.045) 1px, transparent 1px), " +
          "linear-gradient(90deg, rgba(6,182,212,0.045) 1px, transparent 1px)",
        backgroundSize: "50px 50px",
        animation: "gridPan 18s linear infinite",
      }} />

      {/* Orb 1 — top-right, blue */}
      <div style={{
        position: "absolute", width: 700, height: 700, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(59,130,246,0.09) 0%, transparent 68%)",
        top: -300, right: -200,
        animation: "float1 18s ease-in-out infinite",
      }} />

      {/* Orb 2 — bottom-left, cyan */}
      <div style={{
        position: "absolute", width: 500, height: 500, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(6,182,212,0.08) 0%, transparent 68%)",
        bottom: -200, left: -150,
        animation: "float2 22s ease-in-out infinite",
      }} />

      {/* Orb 3 — mid-right, purple accent */}
      <div style={{
        position: "absolute", width: 350, height: 350, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 68%)",
        top: "45%", right: "25%",
        animation: "float3 26s ease-in-out infinite",
      }} />

      {/* Vignette */}
      <div style={{
        position: "absolute", inset: 0,
        background: "radial-gradient(ellipse at center, transparent 40%, rgba(2,11,24,0.7) 100%)",
      }} />
    </div>
  );
}

export default function Layout() {
  return (
    <div style={{ minHeight: "100vh", position: "relative" }}>
      <Background />

      {/* Sticky top nav */}
      <nav className="anim-nav" style={{
        position: "sticky", top: 0, zIndex: 100,
        height: 58,
        background: "rgba(2, 8, 20, 0.88)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(6,182,212,0.12)",
        display: "flex", alignItems: "center",
        padding: "0 28px", gap: 0,
      }}>
        {/* Logo mark */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginRight: 36 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8,
            background: "linear-gradient(135deg, rgba(6,182,212,0.3), rgba(59,130,246,0.2))",
            border: "1px solid rgba(6,182,212,0.4)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14, color: "#06b6d4",
            boxShadow: "0 0 14px rgba(6,182,212,0.25)",
          }}>
            ⬡
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#06b6d4", letterSpacing: "0.06em" }}>
              NETSEC
            </div>
            <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: "0.14em" }}>
              LOG ANALYZER
            </div>
          </div>
        </div>

        {/* Nav links */}
        <div style={{ display: "flex", alignItems: "center", gap: 2, flex: 1 }}>
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              <span style={{ marginRight: 5, opacity: 0.65, fontSize: 11 }}>{icon}</span>
              {label}
            </NavLink>
          ))}
        </div>

        {/* Live status */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 7, height: 7, borderRadius: "50%",
            background: "#22c55e",
            boxShadow: "0 0 8px #22c55e",
            animation: "pulseDot 2.5s ease-in-out infinite",
          }} />
          <span style={{ fontSize: 10, color: "#334155", letterSpacing: "0.08em" }}>
            API :8000
          </span>
        </div>
      </nav>

      {/* Page content */}
      <main style={{
        position: "relative", zIndex: 1,
        maxWidth: 1280, margin: "0 auto",
        padding: "36px 36px 64px",
      }}>
        <Outlet />
      </main>
    </div>
  );
}
