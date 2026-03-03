import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Study } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import { useRole } from "../context/RoleContext";

type SortKey = "irb" | "title" | "pi" | "status" | "expiration" | "created";
type SortDir = "asc" | "desc";

const STATUS_OPTIONS: Array<{ value: Study["status"] | ""; label: string }> = [
  { value: "", label: "All statuses" },
  { value: "pending_researcher", label: "Requestor Pending" },
  { value: "pending_broker", label: "Broker Pending" },
  { value: "active", label: "Active" },
  { value: "completed", label: "Completed" },
  { value: "archived", label: "Archived" },
  { value: "rejected", label: "Rejected" },
];

function getSortValue(s: Study, key: SortKey): string {
  switch (key) {
    case "irb":
      return s.irb_pro_number;
    case "title":
      return s.title;
    case "pi":
      return s.pi_name;
    case "status":
      return s.status;
    case "expiration":
      return s.expiration_alert_date ?? "";
    case "created":
      return s.created_at;
  }
}

export default function StudyList() {
  const [studies, setStudies] = useState<Study[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { role } = useRole();
  const isBroker = role === "broker";

  const [statusFilter, setStatusFilter] = useState<Study["status"] | "">("");
  const [sortKey, setSortKey] = useState<SortKey>("created");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const load = () => {
    setLoading(true);
    api.listStudies().then(setStudies).finally(() => setLoading(false));
  };

  useEffect(load, [role]);

  const filtered = useMemo(() => {
    let list = studies;
    if (statusFilter) {
      list = list.filter((s) => s.status === statusFilter);
    }
    const sorted = [...list].sort((a, b) => {
      const av = getSortValue(a, sortKey);
      const bv = getSortValue(b, sortKey);
      const cmp = av.localeCompare(bv);
      return sortDir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [studies, statusFilter, sortKey, sortDir]);

  const pendingCount = studies.filter((s) => s.status === "pending_broker").length;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const SortHeader = ({ label, col }: { label: string; col: SortKey }) => (
    <button
      onClick={() => handleSort(col)}
      className="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wider text-gray-500 hover:text-gray-700"
    >
      {label}
      {sortKey === col && (
        <span className="text-gray-400">{sortDir === "asc" ? "\u25B2" : "\u25BC"}</span>
      )}
    </button>
  );

  const columns = [
    {
      key: "irb",
      headerNode: <SortHeader label="IRB PRO #" col="irb" />,
      render: (s: Study) => s.irb_pro_number,
    },
    {
      key: "title",
      headerNode: <SortHeader label="Title" col="title" />,
      render: (s: Study) => s.title,
    },
    {
      key: "pi",
      headerNode: <SortHeader label="PI" col="pi" />,
      render: (s: Study) => s.pi_name,
    },
    {
      key: "status",
      headerNode: <SortHeader label="Status" col="status" />,
      render: (s: Study) => <StatusBadge status={s.status} />,
    },
    {
      key: "expiration",
      headerNode: <SortHeader label="Expiration" col="expiration" />,
      render: (s: Study) => {
        if (!s.expiration_alert_date) return "\u2014";
        const isExpired = s.expiration_alert_date <= new Date().toISOString().slice(0, 10);
        if (isExpired) {
          return (
            <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
              Expired {s.expiration_alert_date}
            </span>
          );
        }
        return s.expiration_alert_date;
      },
    },
    {
      key: "created",
      headerNode: <SortHeader label="Created" col="created" />,
      render: (s: Study) => new Date(s.created_at).toLocaleDateString(),
    },
  ];

  return (
    <div>
      {role === "researcher" && (
        <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <h2 className="text-sm font-semibold text-blue-900">Welcome to Airlock</h2>
          <p className="mt-1 text-sm text-blue-800">
            Airlock is Houston Methodist's research data broker. Submit a data request with your
            IRB protocol details, then upload your patient/accession CSV. A broker will review
            and approve your dataset.
          </p>
          <p className="mt-1 text-sm text-blue-700">
            Need to reidentify a patient? Open your study and use the "Request Reidentification"
            button.
          </p>
        </div>
      )}

      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">Studies</h1>
          {isBroker && pendingCount > 0 && (
            <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">
              {pendingCount} pending
            </span>
          )}
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as Study["status"] | "")}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {columns.map((col) => (
                  <th key={col.key} className="px-4 py-3 text-left">
                    {col.headerNode}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {filtered.map((row) => (
                <tr
                  key={row.id}
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => navigate(`/studies/${row.id}`)}
                >
                  {columns.map((col) => (
                    <td key={col.key} className="whitespace-nowrap px-4 py-3 text-sm text-gray-900">
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="px-4 py-8 text-center text-sm text-gray-500"
                  >
                    No data
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
