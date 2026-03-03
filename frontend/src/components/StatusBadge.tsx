const COLORS: Record<string, string> = {
  pending_researcher: "bg-amber-100 text-amber-700",
  pending_broker: "bg-indigo-100 text-indigo-700",
  active: "bg-green-100 text-green-700",
  completed: "bg-blue-100 text-blue-700",
  archived: "bg-yellow-100 text-yellow-700",
  rejected: "bg-red-100 text-red-700",
  pending: "bg-amber-100 text-amber-700",
  approved: "bg-green-100 text-green-700",
  denied: "bg-red-100 text-red-700",
};

const LABELS: Record<string, string> = {
  pending_researcher: "Requestor Pending",
  pending_broker: "Broker Pending",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        COLORS[status] ?? "bg-gray-100 text-gray-700"
      }`}
    >
      {LABELS[status] ?? status}
    </span>
  );
}
