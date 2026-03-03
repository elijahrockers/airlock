import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, TemporalPolicy } from "../api/client";
import { useRole } from "../context/RoleContext";

export default function NewStudy() {
  const navigate = useNavigate();
  const { role } = useRole();

  if (role === "broker") {
    return (
      <div className="rounded-lg border border-amber-200 border-l-4 border-l-amber-400 bg-amber-50 p-6">
        <h2 className="text-lg font-semibold text-amber-900">Researchers Only</h2>
        <p className="mt-2 text-sm text-amber-800">
          Only researchers can create new study requests. Switch to the researcher role to submit a request.
        </p>
      </div>
    );
  }

  const [form, setForm] = useState({
    irb_pro_number: "",
    title: "",
    pi_name: "",
    description: "",
    requestor: "",
    temporal_policy: "removed" as TemporalPolicy,
    expiration_alert_date: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const { expiration_alert_date, ...rest } = form;
      const study = await api.createStudy({
        ...rest,
        expiration_alert_date: expiration_alert_date || null,
      });

      navigate(`/studies/${study.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create study");
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        New Data Request
      </h1>

      <form onSubmit={submit} className="mx-auto max-w-2xl">
        {error && (
          <div className="mb-4 rounded-md border border-red-200 border-l-4 border-l-red-400 bg-red-50 p-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-gray-900">Study Details</h2>

          {(["irb_pro_number", "title", "pi_name", "requestor"] as const).map((field) => (
            <label key={field} className="block">
              <span className="text-sm font-medium text-gray-700">
                {field.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </span>
              <input
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm transition-colors duration-150 focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
                value={form[field]}
                onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                required={field !== "requestor"}
              />
            </label>
          ))}
          <label className="block">
            <span className="text-sm font-medium text-gray-700">Description</span>
            <textarea
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>

          <div className="grid grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm font-medium text-gray-700">Temporal Policy</span>
              <select
                value={form.temporal_policy}
                onChange={(e) =>
                  setForm({ ...form, temporal_policy: e.target.value as TemporalPolicy })
                }
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm transition-colors duration-150 focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="removed">Removed</option>
                <option value="shifted">Shifted</option>
                <option value="unshifted">Unshifted</option>
              </select>
            </label>

            <label className="block">
              <span className="text-sm font-medium text-gray-700">Expiration Alert Date</span>
              <input
                type="date"
                value={form.expiration_alert_date}
                onChange={(e) => setForm({ ...form, expiration_alert_date: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm transition-colors duration-150 focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
              />
            </label>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors duration-150 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors duration-150 hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Submitting..." : "Submit Request"}
          </button>
        </div>
      </form>
    </div>
  );
}
