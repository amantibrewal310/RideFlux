import { Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import AppShell from "./components/layout/AppShell";
import DashboardPage from "./pages/DashboardPage";
import RidesPage from "./pages/RidesPage";
import DriversPage from "./pages/DriversPage";
import { useWebSocket } from "./hooks/useWebSocket";
import Toast from "./components/common/Toast";

function App() {
  const { connect, disconnect } = useWebSocket();

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return (
    <>
      <AppShell>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/rides" element={<RidesPage />} />
          <Route path="/drivers" element={<DriversPage />} />
        </Routes>
      </AppShell>
      <Toast />
    </>
  );
}

export default App;
