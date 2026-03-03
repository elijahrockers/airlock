import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Study } from "../api/client";
import DataTable from "../components/DataTable";
import StatusBadge from "../components/StatusBadge";
import { useRole } from "../context/RoleContext";

export default function StudyList() {
  const [studies, setStudies] = useState<Study[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { role } = useRole();

  const load = () => {
    setLoading(true);
    api.listStudies().then(setStudies).finally(() => setLoading(false));
  };

  useEffect(load, [role]);

  const pendingCount = studies.filter((s) => s.status === "requested").length;

  const columns = [
    { key: "irb", header: "IRB PRO #", render: (s: Study) => s.irb_pro_number },
    { key: "title", header: "Title", render: (s: Study) => s.title },
    { key: "pi", header: "PI", render: (s: Study) => s.pi_name },
    { key: "status", header: "Status", render: (s: Study) => <StatusBadge status={s.status} /> },
    {
      key: "expiration",
      header: "Expiration",
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
      header: "Created",
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
            IRB protocol details and patient/accession CSV. A broker will review your request and,
            once approved, prepare your deidentified dataset. You can track your requests below.
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
          {role === "broker" && pendingCount > 0 && (
            <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">
              {pendingCount} pending
            </span>
          )}
        </div>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <DataTable
          columns={columns}
          data={studies}
          onRowClick={(s) => navigate(`/studies/${s.id}`)}
        />
      )}
    </div>
  );
}
