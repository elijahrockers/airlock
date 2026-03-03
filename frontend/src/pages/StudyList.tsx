import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Study, TemporalPolicy } from "../api/client";
import DataTable from "../components/DataTable";
import StatusBadge from "../components/StatusBadge";

export default function StudyList() {
  const [studies, setStudies] = useState<Study[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    api.listStudies().then(setStudies).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const columns = [
    { key: "irb", header: "IRB PRO #", render: (s: Study) => s.irb_pro_number },
    { key: "title", header: "Title", render: (s: Study) => s.title },
    { key: "pi", header: "PI", render: (s: Study) => s.pi_name },
    { key: "status", header: "Status", render: (s: Study) => <StatusBadge status={s.status} /> },
    {
      key: "created",
      header: "Created",
      render: (s: Study) => new Date(s.created_at).toLocaleDateString(),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Studies</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          New Study
        </button>
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

      {showCreate && (
        <CreateStudyModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}
    </div>
  );
}

function CreateStudyModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    irb_pro_number: "",
    title: "",
    pi_name: "",
    description: "",
    requestor: "",
    temporal_policy: "removed" as TemporalPolicy,
  });
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createStudy(form);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create study");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <form
        onSubmit={submit}
        className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl"
      >
        <h2 className="mb-4 text-lg font-semibold">New Study</h2>
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
        {(["irb_pro_number", "title", "pi_name", "requestor", "description"] as const).map(
          (field) => (
            <label key={field} className="mb-3 block">
              <span className="text-sm font-medium text-gray-700">
                {field.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </span>
              <input
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                value={form[field]}
                onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                required={field !== "description" && field !== "requestor"}
              />
            </label>
          ),
        )}
        <label className="mb-3 block">
          <span className="text-sm font-medium text-gray-700">Temporal Policy</span>
          <select
            value={form.temporal_policy}
            onChange={(e) =>
              setForm({ ...form, temporal_policy: e.target.value as TemporalPolicy })
            }
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="removed">Removed</option>
            <option value="shifted">Shifted</option>
            <option value="unshifted">Unshifted</option>
          </select>
        </label>
        <div className="mt-4 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Create
          </button>
        </div>
      </form>
    </div>
  );
}
