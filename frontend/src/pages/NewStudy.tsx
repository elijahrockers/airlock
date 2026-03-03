import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, TemporalPolicy, validateCsvHeaders } from "../api/client";
import { useRole } from "../context/RoleContext";

export default function NewStudy() {
  const navigate = useNavigate();
  const { role } = useRole();
  const isResearcher = role === "researcher";

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

  // CSV state
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvError, setCsvError] = useState("");
  const [csvValid, setCsvValid] = useState(false);

  const handleCsvChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setCsvFile(file);
    setCsvError("");
    setCsvValid(false);

    if (!file) return;

    if (!file.name.endsWith(".csv")) {
      setCsvError("File must be a .csv");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const text = reader.result as string;
      const firstLine = text.split(/\r?\n/)[0];
      if (!firstLine) {
        setCsvError("CSV file appears to be empty");
        return;
      }
      const result = validateCsvHeaders(firstLine);
      if (!result.valid) {
        setCsvError(`Missing required columns: ${result.missing.join(", ")}`);
      } else {
        setCsvValid(true);
      }
    };
    reader.readAsText(file);
  };

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

      if (csvFile && csvValid) {
        await api.uploadDatasetCsv(study.id, csvFile);
      }

      navigate(`/studies/${study.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create study");
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        {isResearcher ? "New Data Request" : "New Study"}
      </h1>

      <form onSubmit={submit} className="mx-auto max-w-2xl">
        {error && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="text-base font-semibold text-gray-900">Study Details</h2>

          {(["irb_pro_number", "title", "pi_name", "requestor"] as const).map((field) => (
            <label key={field} className="block">
              <span className="text-sm font-medium text-gray-700">
                {field.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </span>
              <input
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
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
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
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
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </label>
          </div>
        </div>

        {isResearcher && (
          <div className="mt-4 space-y-4 rounded-lg border border-gray-200 bg-white p-6">
            <div>
              <h2 className="text-base font-semibold text-gray-900">Patient / Accession CSV</h2>
              <p className="mt-1 text-sm text-gray-500">
                Upload a CSV with columns: MRN, Subject ID, Accession Number.
                Headers are case-insensitive.
              </p>
            </div>
            <label className="block">
              <span className="text-sm font-medium text-gray-700">CSV File (optional)</span>
              <input
                type="file"
                accept=".csv"
                onChange={handleCsvChange}
                className="mt-1 block w-full text-sm"
              />
            </label>
            {csvError && (
              <div className="rounded-md border border-red-200 bg-red-50 p-3">
                <p className="text-sm text-red-700">{csvError}</p>
              </div>
            )}
            {csvValid && csvFile && (
              <div className="rounded-md border border-green-200 bg-green-50 p-3">
                <p className="text-sm text-green-700">
                  Headers valid &mdash; {csvFile.name} ready to upload
                </p>
              </div>
            )}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || (!!csvFile && !csvValid)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting
              ? "Submitting..."
              : isResearcher
                ? "Submit Request"
                : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}
