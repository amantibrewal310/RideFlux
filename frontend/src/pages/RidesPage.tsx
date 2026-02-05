import { useState } from "react";
import RideList from "../components/rides/RideList";

const STATUSES = [
  "all",
  "matching",
  "offered",
  "accepted",
  "in_progress",
  "completed",
  "cancelled",
  "no_drivers",
];

export default function RidesPage() {
  const [filter, setFilter] = useState("all");

  return (
    <div className="page-rides">
      <div className="page-header">
        <h2 className="page-title">Rides</h2>
        <div className="filter-bar">
          {STATUSES.map((s) => (
            <button
              key={s}
              className={`btn btn-filter${filter === s ? " btn-filter--active" : ""}`}
              onClick={() => setFilter(s)}
            >
              {s === "all" ? "All" : s.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      <RideList statusFilter={filter === "all" ? undefined : filter} />
    </div>
  );
}
