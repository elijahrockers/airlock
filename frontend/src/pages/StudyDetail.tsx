import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  api,
  AccessionMapping,
  DatasetManifest,
  DatasetUploadResponse,
  PatientMapping,
  Study,
} from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import DataTable from "../components/DataTable";
import StatusBadge from "../components/StatusBadge";

export default function StudyDetail() {
  const { id } = useParams<{ id: string }>();
  const [study, setStudy] = useState<Study | null>(null);
  const [patients, setPatients] = useState<PatientMapping[]>([]);
  const [datasets, setDatasets] = useState<DatasetManifest[]>([]);
  const [accessions, setAccessions] = useState<AccessionMapping[]>([]);

  // MRN reveal state
  const [revealedMrns, setRevealedMrns] = useState<Record<string, string>>({});
  const [revealingId, setRevealingId] = useState<string | null>(null);
  const [revealingAll, setRevealingAll] = useState(false);
  const [showConfirmRevealAll, setShowConfirmRevealAll] = useState(false);

  // Accession reveal state
  const [revealedAccessions, setRevealedAccessions] = useState<
    Record<string, { accession: string; subject: string }>
  >({});
  const [revealingAccId, setRevealingAccId] = useState<string | null>(null);
  const [revealingAllAcc, setRevealingAllAcc] = useState(false);
  const [showConfirmRevealAllAcc, setShowConfirmRevealAllAcc] = useState(false);

  // Dataset detail state
  const [expandedDatasetId, setExpandedDatasetId] = useState<string | null>(null);

  // Upload modal state
  const [showUpload, setShowUpload] = useState(false);

  const loadAll = () => {
    if (!id) return;
    api.getStudy(id).then(setStudy);
    api.listPatients(id).then(setPatients);
    api.listDatasets(id).then(setDatasets);
    api.listAccessions(id).then(setAccessions);
  };

  useEffect(loadAll, [id]);

  // MRN reveal handlers
  const handleRevealOne = async (patientId: string) => {
    if (!id) return;
    setRevealingId(patientId);
    try {
      const result = await api.revealPatient(id, patientId);
      setRevealedMrns((prev) => ({ ...prev, [patientId]: result.mrn! }));
    } finally {
      setRevealingId(null);
    }
  };

  const handleRevealAll = async () => {
    if (!id) return;
    setShowConfirmRevealAll(false);
    setRevealingAll(true);
    try {
      const result = await api.revealAllPatients(id);
      const mrns: Record<string, string> = {};
      for (const p of result.patients) {
        mrns[p.id] = p.mrn!;
      }
      setRevealedMrns(mrns);
    } finally {
      setRevealingAll(false);
    }
  };

  // Accession reveal handlers
  const handleRevealAccession = async (accId: string) => {
    if (!id) return;
    setRevealingAccId(accId);
    try {
      const result = await api.revealAccession(id, accId);
      setRevealedAccessions((prev) => ({
        ...prev,
        [accId]: {
          accession: result.accession_number!,
          subject: result.subject_id!,
        },
      }));
    } finally {
      setRevealingAccId(null);
    }
  };

  const handleRevealAllAccessions = async () => {
    if (!id) return;
    setShowConfirmRevealAllAcc(false);
    setRevealingAllAcc(true);
    try {
      const result = await api.revealAllAccessions(id);
      const revealed: Record<string, { accession: string; subject: string }> =
        {};
      for (const a of result.accessions) {
        revealed[a.id] = {
          accession: a.accession_number!,
          subject: a.subject_id!,
        };
      }
      setRevealedAccessions(revealed);
    } finally {
      setRevealingAllAcc(false);
    }
  };

  if (!study) return <p className="text-gray-500">Loading...</p>;

  const expandedDataset = datasets.find((d) => d.id === expandedDatasetId);

  return (
    <div className="space-y-8">
      {/* Study header */}
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">{study.title}</h1>
          <StatusBadge status={study.status} />
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="font-medium text-gray-500">IRB PRO #</dt>
            <dd>{study.irb_pro_number}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">PI</dt>
            <dd>{study.pi_name}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">Requestor</dt>
            <dd>{study.requestor ?? "—"}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">Created</dt>
            <dd>{new Date(study.created_at).toLocaleString()}</dd>
          </div>
          {study.description && (
            <div className="col-span-2">
              <dt className="font-medium text-gray-500">Description</dt>
              <dd>{study.description}</dd>
            </div>
          )}
        </dl>
      </div>

      {/* Patient Mappings */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Patient Mappings ({patients.length})
          </h2>
          <div className="flex gap-2">
            {Object.keys(revealedMrns).length > 0 && (
              <button
                onClick={() => setRevealedMrns({})}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                Hide All MRNs
              </button>
            )}
            <button
              onClick={() => setShowConfirmRevealAll(true)}
              disabled={revealingAll}
              className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50"
            >
              {revealingAll ? "Revealing..." : "Reveal All MRNs"}
            </button>
          </div>
        </div>
        <DataTable
          columns={[
            {
              key: "mrn",
              header: "MRN",
              render: (p: PatientMapping) => {
                const revealed = revealedMrns[p.id];
                if (revealed) {
                  return (
                    <span className="font-mono text-sm">{revealed}</span>
                  );
                }
                return (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRevealOne(p.id);
                    }}
                    disabled={revealingId === p.id}
                    className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                    title="Reveal MRN (audit-logged)"
                  >
                    {revealingId === p.id ? (
                      "..."
                    ) : (
                      <>
                        <EyeIcon />
                        Reveal
                      </>
                    )}
                  </button>
                );
              },
            },
            {
              key: "subject",
              header: "Subject ID",
              render: (p: PatientMapping) => p.subject_id,
            },
            {
              key: "created",
              header: "Added",
              render: (p: PatientMapping) =>
                new Date(p.created_at).toLocaleDateString(),
            },
          ]}
          data={patients}
        />
      </section>

      {/* Dataset Manifests */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Dataset Manifests ({datasets.length})
          </h2>
          <button
            onClick={() => setShowUpload(true)}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
          >
            Upload Dataset
          </button>
        </div>
        <DataTable
          columns={[
            {
              key: "type",
              header: "Type",
              render: (d: DatasetManifest) => d.dataset_type,
            },
            {
              key: "desc",
              header: "Description",
              render: (d: DatasetManifest) => d.description ?? "—",
            },
            {
              key: "records",
              header: "Records",
              render: (d: DatasetManifest) =>
                d.record_count?.toLocaleString() ?? "—",
            },
            {
              key: "keyver",
              header: "Key Version",
              render: (d: DatasetManifest) => `v${d.global_key_version}`,
            },
            {
              key: "keyid",
              header: "Key ID",
              render: (d: DatasetManifest) => (
                <span
                  className="font-mono text-xs text-gray-500"
                  title={d.global_hash_key_id}
                >
                  {d.global_hash_key_id.slice(0, 8)}...
                </span>
              ),
            },
            {
              key: "created",
              header: "Created",
              render: (d: DatasetManifest) =>
                new Date(d.created_at).toLocaleDateString(),
            },
          ]}
          data={datasets}
          onRowClick={(d) =>
            setExpandedDatasetId(expandedDatasetId === d.id ? null : d.id)
          }
        />
        {expandedDataset && (
          <div className="mt-2 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-900">
                Dataset Details
              </h3>
              <button
                onClick={() => setExpandedDatasetId(null)}
                className="text-xs text-gray-500 hover:text-gray-700"
              >
                Close
              </button>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
              <div>
                <dt className="font-medium text-gray-500">Dataset ID</dt>
                <dd className="font-mono text-xs">{expandedDataset.id}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">
                  Global Hash Key ID
                </dt>
                <dd className="font-mono text-xs">
                  {expandedDataset.global_hash_key_id}
                </dd>
              </div>
            </dl>
            <div className="mt-3">
              <dt className="text-sm font-medium text-gray-500">Metadata</dt>
              <dd className="mt-1">
                {expandedDataset.metadata_json ? (
                  <pre className="max-h-64 overflow-auto rounded border border-gray-200 bg-white p-3 text-xs text-gray-800">
                    {JSON.stringify(expandedDataset.metadata_json, null, 2)}
                  </pre>
                ) : (
                  <span className="text-sm italic text-gray-400">
                    No metadata
                  </span>
                )}
              </dd>
            </div>
          </div>
        )}
      </section>

      {/* Accession Mappings */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Accession Mappings ({accessions.length})
          </h2>
          <div className="flex gap-2">
            {Object.keys(revealedAccessions).length > 0 && (
              <button
                onClick={() => setRevealedAccessions({})}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                Hide All Accessions
              </button>
            )}
            {accessions.length > 0 && (
              <button
                onClick={() => setShowConfirmRevealAllAcc(true)}
                disabled={revealingAllAcc}
                className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50"
              >
                {revealingAllAcc ? "Revealing..." : "Reveal All Accessions"}
              </button>
            )}
          </div>
        </div>
        <DataTable
          columns={[
            {
              key: "accession",
              header: "Accession #",
              render: (a: AccessionMapping) => {
                const revealed = revealedAccessions[a.id];
                if (revealed) {
                  return (
                    <span className="font-mono text-sm">
                      {revealed.accession}
                    </span>
                  );
                }
                return (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRevealAccession(a.id);
                    }}
                    disabled={revealingAccId === a.id}
                    className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                    title="Reveal accession (audit-logged)"
                  >
                    {revealingAccId === a.id ? (
                      "..."
                    ) : (
                      <>
                        <EyeIcon />
                        Reveal
                      </>
                    )}
                  </button>
                );
              },
            },
            {
              key: "subject",
              header: "Subject ID",
              render: (a: AccessionMapping) =>
                revealedAccessions[a.id]?.subject ?? "—",
            },
            {
              key: "dataset",
              header: "Dataset",
              render: (a: AccessionMapping) => (
                <span
                  className="font-mono text-xs text-gray-500"
                  title={a.dataset_manifest_id}
                >
                  {a.dataset_manifest_id.slice(0, 8)}...
                </span>
              ),
            },
            {
              key: "created",
              header: "Added",
              render: (a: AccessionMapping) =>
                new Date(a.created_at).toLocaleDateString(),
            },
          ]}
          data={accessions}
        />
      </section>

      {/* Dialogs */}
      <ConfirmDialog
        open={showConfirmRevealAll}
        title="Reveal All MRNs"
        message={`This will decrypt and display all ${patients.length} MRNs for this study. This action is audit-logged. Continue?`}
        onConfirm={handleRevealAll}
        onCancel={() => setShowConfirmRevealAll(false)}
      />
      <ConfirmDialog
        open={showConfirmRevealAllAcc}
        title="Reveal All Accessions"
        message={`This will decrypt and display all ${accessions.length} accession numbers for this study. This action is audit-logged. Continue?`}
        onConfirm={handleRevealAllAccessions}
        onCancel={() => setShowConfirmRevealAllAcc(false)}
      />

      {showUpload && (
        <UploadDatasetModal
          studyId={id!}
          onClose={() => setShowUpload(false)}
          onUploaded={() => {
            setShowUpload(false);
            loadAll();
          }}
        />
      )}
    </div>
  );
}

function EyeIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
      />
    </svg>
  );
}

const DATASET_TYPES = [
  "dicom_images",
  "clinical_data",
  "pathology",
  "genomics",
  "other",
];

function UploadDatasetModal({
  studyId,
  onClose,
  onUploaded,
}: {
  studyId: string;
  onClose: () => void;
  onUploaded: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [datasetType, setDatasetType] = useState("dicom_images");
  const [description, setDescription] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<DatasetUploadResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const resp = await api.uploadDatasetCsv(
        studyId,
        file,
        datasetType,
        description || undefined,
      );
      setResult(resp);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  if (result) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
          <h2 className="mb-4 text-lg font-semibold text-green-700">
            Upload Complete
          </h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Patients created</dt>
              <dd className="font-medium">{result.patients_created}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Patients reused</dt>
              <dd className="font-medium">{result.patients_reused}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Accessions created</dt>
              <dd className="font-medium">{result.accessions_created}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Global key version</dt>
              <dd className="font-medium">
                v{result.manifest.global_key_version}
              </dd>
            </div>
          </dl>
          <div className="mt-4 flex justify-end">
            <button
              onClick={onUploaded}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl"
      >
        <h2 className="mb-4 text-lg font-semibold">Upload Dataset</h2>
        <p className="mb-4 text-sm text-gray-600">
          Upload a CSV with columns: MRN, Subject ID, Accession Number
        </p>
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
        <label className="mb-3 block">
          <span className="text-sm font-medium text-gray-700">CSV File</span>
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="mt-1 block w-full text-sm"
            required
          />
        </label>
        <label className="mb-3 block">
          <span className="text-sm font-medium text-gray-700">
            Dataset Type
          </span>
          <select
            value={datasetType}
            onChange={(e) => setDatasetType(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            {DATASET_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </label>
        <label className="mb-3 block">
          <span className="text-sm font-medium text-gray-700">
            Description (optional)
          </span>
          <input
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
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
            disabled={!file || uploading}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
      </form>
    </div>
  );
}
