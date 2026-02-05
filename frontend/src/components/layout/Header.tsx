import StatusIndicator from "../common/StatusIndicator";
import WebSocketClient from "../../api/ws";
import { useEffect, useState } from "react";

export default function Header() {
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setWsConnected(WebSocketClient.getInstance().connected);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="header">
      <div className="header-brand">
        <h1 className="header-title">RideFlux</h1>
        <span className="header-subtitle">Real-time Dashboard</span>
      </div>
      <div className="header-status">
        <StatusIndicator
          status={wsConnected ? "connected" : "disconnected"}
        />
        <span className="header-status-text">
          {wsConnected ? "Live" : "Disconnected"}
        </span>
      </div>
    </header>
  );
}
