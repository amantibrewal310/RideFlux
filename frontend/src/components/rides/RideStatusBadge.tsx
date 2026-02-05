interface Props {
  status: string;
}

const STATUS_COLORS: Record<string, string> = {
  requested: "badge--yellow",
  matching: "badge--yellow",
  offered: "badge--orange",
  matched: "badge--blue",
  accepted: "badge--blue",
  in_progress: "badge--indigo",
  in_trip: "badge--indigo",
  completed: "badge--green",
  paid: "badge--green",
  cancelled: "badge--red",
  no_drivers: "badge--red",
};

export default function RideStatusBadge({ status }: Props) {
  const colorClass = STATUS_COLORS[status] ?? "badge--gray";
  return (
    <span className={`badge ${colorClass}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
