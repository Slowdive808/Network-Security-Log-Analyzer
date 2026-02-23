import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import Events from "./pages/Events";
import Anomalies from "./pages/Anomalies";
import Reports from "./pages/Reports";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="upload" element={<Upload />} />
        <Route path="events" element={<Events />} />
        <Route path="anomalies" element={<Anomalies />} />
        <Route path="reports" element={<Reports />} />
      </Route>
    </Routes>
  );
}
