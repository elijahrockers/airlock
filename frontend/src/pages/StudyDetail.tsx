import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  api,
  AccessionMapping,
  DatasetManifest,
  DatasetUploadResponse,
  PatientMapping,
  ReidentificationRequest,
  Study,
} from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import DataTable from "../components/DataTable";
import StatusBadge from "../components/StatusBadge";
import { useRole } from "../context/RoleContext";

export default function StudyDetail() {
  const { id } = useParams<{ id: string }>();
  const { role } = useRole();
  const isBroker = role === "broker";

  const [study, setStudy] = useState<Study | null>(null);
  const [patients, setPatients] = useState<PatientMapping[]>([]);
  const [datasets, setDatasets] = useState<DatasetManifest[]>([]);
  const [accessions, setAccessions] = useState<AccessionMapping[]>([]);

  // MRN reveal state
  const [revealedMrns, setRevealedMrns] = useState<
    Record<string, { mrn: string; offset: number | null }>
  >({});
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

  // Reidentification state
  const [reidentRequests, setReidentRequests] = useState<ReidentificationRequest[]>([]);
  const [showReidentModal, setShowReidentModal] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const loadAll = () => {
    if (!id) return;
    api.getStudy(id).then(setStudy);
    api.listPatients(id).then(setPatients);
    api.listDatasets(id).then(setDatasets);
    api.listAccessions(id).then(setAccessions);
    api.listReidentificationRequests(id).then(setReidentRequests);
  };

  useEffect(loadAll, [id]);

  // MRN reveal handlers
  const handleRevealOne = async (patientId: string) => {
    if (!id) return;
    setRevealingId(patientId);
    try {
      const result = await api.revealPatient(id, patientId);
      setRevealedMrns((prev) => ({
        ...prev,
        [patientId]: { mrn: result.mrn!, offset: result.date_offset_days ?? null },
      }));
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
      const mrns: Record<string, { mrn: string; offset: number | null }> = {};
      for (const p of result.patients) {
        mrns[p.id] = { mrn: p.mrn!, offset: p.date_offset_days ?? null };
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

  const handleReject = async () => {
    if (!id) return;
    const updated = await api.rejectStudy(id);
    setStudy(updated);
  };

  const handleApproveDataset = async (datasetId: string) => {
    if (!id) return;
    await api.approveDataset(id, datasetId);
    loadAll();
  };

  const handleResolve = async (requestId: string, status: "completed" | "denied") => {
    if (!id) return;
    setResolvingId(requestId);
    try {
      await api.resolveReidentificationRequest(id, requestId, status);
      api.listReidentificationRequests(id).then(setReidentRequests);
    } finally {
      setResolvingId(null);
    }
  };

  const canRequestReident =
    !isBroker && study?.status !== "pending_researcher" && study?.status !== "rejected" && study?.status !== "archived";

  if (!study) return (
    <div className="flex items-center justify-center gap-3 py-12">
      <div className="spinner" />
      <span className="text-sm text-gray-500">Loading study...</span>
    </div>
  );

  const expandedDataset = datasets.find((d) => d.id === expandedDatasetId);
  const canUpload = !isBroker && (study.status === "pending_researcher" || study.status === "active");

  return (
    <div className="space-y-8">
      {/* Study header */}
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">{study.title}</h1>
          <StatusBadge status={study.status} />
          {isBroker && (study.status === "pending_researcher" || study.status === "pending_broker") && (
            <button
              onClick={handleReject}
              className="rounded-md bg-red-600 px-3 py-1 text-xs font-medium text-white transition-colors duration-150 hover:bg-red-700"
            >
              Reject
            </button>
          )}
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
            <dd>{study.requestor ?? "\u2014"}</dd>
          </div>
          {study.requested_by && (
            <div>
              <dt className="font-medium text-gray-500">Requested By</dt>
              <dd>{study.requested_by}</dd>
            </div>
          )}
          <div>
            <dt className="font-medium text-gray-500">Temporal Policy</dt>
            <dd className="capitalize">{study.temporal_policy}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">Expiration Alert</dt>
            <dd>
              {!study.expiration_alert_date
                ? "\u2014"
                : study.expiration_alert_date <= new Date().toISOString().slice(0, 10)
                  ? (
                    <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                      Expired {study.expiration_alert_date}
                    </span>
                  )
                  : study.expiration_alert_date}
            </dd>
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
          {isBroker && (
            <div className="flex gap-2">
              {Object.keys(revealedMrns).length > 0 && (
                <button
                  onClick={() => setRevealedMrns({})}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors duration-150 hover:bg-gray-50"
                >
                  Hide All MRNs
                </button>
              )}
              <button
                onClick={() => setShowConfirmRevealAll(true)}
                disabled={revealingAll}
                className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-medium text-white transition-colors duration-150 hover:bg-amber-700 disabled:opacity-50"
              >
                {revealingAll ? "Revealing..." : "Reveal All MRNs"}
              </button>
            </div>
          )}
        </div>
        <DataTable
          columns={[
            {
              key: "mrn",
              header: "MRN",
              render: (p: PatientMapping) => {
                if (!isBroker) {
                  return <span className="text-xs text-gray-400">***</span>;
                }
                const revealed = revealedMrns[p.id];
                if (revealed) {
                  return (
                    <span className="font-mono text-sm">{revealed.mrn}</span>
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
            ...(study.temporal_policy === "shifted"
              ? [
                  {
                    key: "offset",
                    header: "Date Offset (days)",
                    render: (p: PatientMapping) => {
                      if (!isBroker) {
                        return <span className="text-xs text-gray-400">***</span>;
                      }
                      const revealed = revealedMrns[p.id];
                      if (revealed) {
                        return (
                          <span className="font-mono text-sm">
                            {revealed.offset}
                          </span>
                        );
                      }
                      return (
                        <span className="text-xs italic text-gray-400">
                          Reveal MRN first
                        </span>
                      );
                    },
                  },
                ]
              : []),
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

      {/* Researcher guidance banners */}
      {!isBroker && study.status === "pending_researcher" && (
        <div className="rounded-lg border border-blue-200 border-l-4 border-l-blue-400 bg-blue-50 p-4">
          <p className="text-sm text-blue-800">
            Upload your patient/accession CSV below to submit this study for broker review.
          </p>
        </div>
      )}
      {!isBroker && study.status === "pending_broker" && (
        <div className="rounded-lg border border-indigo-200 border-l-4 border-l-indigo-400 bg-indigo-50 p-4">
          <p className="text-sm text-indigo-800">
            Your dataset has been submitted and is awaiting broker approval.
          </p>
        </div>
      )}

      {/* Dataset Manifests */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Dataset Manifests ({datasets.length})
          </h2>
          {canUpload && (
            <button
              onClick={() => setShowUpload(true)}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors duration-150 hover:bg-blue-700"
            >
              Upload Dataset
            </button>
          )}
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
              render: (d: DatasetManifest) => d.description ?? "\u2014",
            },
            {
              key: "records",
              header: "Records",
              render: (d: DatasetManifest) =>
                d.record_count?.toLocaleString() ?? "\u2014",
            },
            {
              key: "status",
              header: "Status",
              render: (d: DatasetManifest) => (
                <div className="flex items-center gap-2">
                  <StatusBadge status={d.status} />
                  {isBroker && d.status === "pending" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleApproveDataset(d.id);
                      }}
                      className="rounded-md bg-green-600 px-2 py-0.5 text-xs font-medium text-white transition-colors duration-150 hover:bg-green-700"
                    >
                      Approve
                    </button>
                  )}
                </div>
              ),
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
          <div className="mt-2 rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-900">
                Dataset Details
              </h3>
              <button
                onClick={() => setExpandedDatasetId(null)}
                className="text-xs text-gray-500 transition-colors duration-150 hover:text-gray-700"
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
          {isBroker && (
            <div className="flex gap-2">
              {Object.keys(revealedAccessions).length > 0 && (
                <button
                  onClick={() => setRevealedAccessions({})}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors duration-150 hover:bg-gray-50"
                >
                  Hide All Accessions
                </button>
              )}
              {accessions.length > 0 && (
                <button
                  onClick={() => setShowConfirmRevealAllAcc(true)}
                  disabled={revealingAllAcc}
                  className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-medium text-white transition-colors duration-150 hover:bg-amber-700 disabled:opacity-50"
                >
                  {revealingAllAcc ? "Revealing..." : "Reveal All Accessions"}
                </button>
              )}
            </div>
          )}
        </div>
        <DataTable
          columns={[
            {
              key: "accession",
              header: "Accession #",
              render: (a: AccessionMapping) => {
                if (!isBroker) {
                  return <span className="text-xs text-gray-400">***</span>;
                }
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
                isBroker
                  ? (revealedAccessions[a.id]?.subject ?? "\u2014")
                  : "\u2014",
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

      {/* Reidentification Requests */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Reidentification Requests ({reidentRequests.length})
          </h2>
          {canRequestReident && (
            <button
              onClick={() => setShowReidentModal(true)}
              className="rounded-md bg-purple-600 px-3 py-1.5 text-xs font-medium text-white transition-colors duration-150 hover:bg-purple-700"
            >
              Request Reidentification
            </button>
          )}
        </div>
        {reidentRequests.length === 0 ? (
          <p className="text-sm text-gray-500">No reidentification requests.</p>
        ) : (
          <div className="space-y-3">
            {reidentRequests.map((req) => (
              <div
                key={req.id}
                className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition-shadow duration-150 hover:shadow-md"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900">
                      {req.requested_by}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(req.created_at).toLocaleString()}
                    </span>
                    <StatusBadge status={req.status} />
                  </div>
                  {isBroker && req.status === "pending" && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleResolve(req.id, "completed")}
                        disabled={resolvingId === req.id}
                        className="rounded-md bg-green-600 px-3 py-1 text-xs font-medium text-white transition-colors duration-150 hover:bg-green-700 disabled:opacity-50"
                      >
                        Complete
                      </button>
                      <button
                        onClick={() => handleResolve(req.id, "denied")}
                        disabled={resolvingId === req.id}
                        className="rounded-md bg-red-600 px-3 py-1 text-xs font-medium text-white transition-colors duration-150 hover:bg-red-700 disabled:opacity-50"
                      >
                        Deny
                      </button>
                    </div>
                  )}
                </div>
                <p className="mt-2 text-sm text-gray-700">{req.message}</p>
                {req.resolved_at && (
                  <p className="mt-1 text-xs text-gray-500">
                    Resolved by {req.resolved_by} on{" "}
                    {new Date(req.resolved_at).toLocaleString()}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
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

      {showReidentModal && (
        <ReidentificationModal
          studyId={id!}
          onClose={() => setShowReidentModal(false)}
          onCreated={() => {
            setShowReidentModal(false);
            api.listReidentificationRequests(id!).then(setReidentRequests);
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
      <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="modal-panel w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
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
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors duration-150 hover:bg-blue-700"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <form
        onSubmit={handleSubmit}
        className="modal-panel w-full max-w-lg rounded-lg bg-white p-6 shadow-xl"
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
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm transition-colors duration-150 focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
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
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm transition-colors duration-150 focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <div className="mt-4 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm transition-colors duration-150 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!file || uploading}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors duration-150 hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
      </form>
    </div>
  );
}

function ReidentificationModal({
  studyId,
  onClose,
  onCreated,
}: {
  studyId: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await api.createReidentificationRequest(studyId, message);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit request");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <form
        onSubmit={handleSubmit}
        className="modal-panel w-full max-w-lg rounded-lg bg-white p-6 shadow-xl"
      >
        <h2 className="mb-4 text-lg font-semibold">Request Reidentification</h2>
        <p className="mb-4 text-sm text-gray-600">
          Describe which patients need to be reidentified and why. A broker will
          review your request.
        </p>
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
        <label className="mb-3 block">
          <span className="text-sm font-medium text-gray-700">Message</span>
          <textarea
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm transition-colors duration-150 focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
            rows={4}
            maxLength={2000}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            required
          />
        </label>
        <div className="mt-4 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm transition-colors duration-150 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!message.trim() || submitting}
            className="rounded-md bg-purple-600 px-4 py-2 text-sm font-medium text-white transition-colors duration-150 hover:bg-purple-700 disabled:opacity-50"
          >
            {submitting ? "Submitting..." : "Submit Request"}
          </button>
        </div>
      </form>
    </div>
  );
}
