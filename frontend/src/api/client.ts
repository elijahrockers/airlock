export type UserRole = "broker" | "researcher";

let currentRole: UserRole = "broker";

export function setApiRole(role: UserRole) {
  currentRole = role;
}

export function getApiRole(): UserRole {
  return currentRole;
}

const BASE = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      "X-User-Role": currentRole,
      ...init?.headers,
    },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type TemporalPolicy = "removed" | "shifted" | "unshifted";

export interface Study {
  id: string;
  irb_pro_number: string;
  title: string;
  description: string | null;
  pi_name: string;
  requestor: string | null;
  requested_by: string | null;
  status: "pending_researcher" | "pending_broker" | "active" | "completed" | "archived" | "rejected";
  temporal_policy: TemporalPolicy;
  expiration_alert_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface GlobalKey {
  id: string;
  version: number;
  is_active: boolean;
  created_at: string;
  retired_at: string | null;
}

export interface PatientMapping {
  id: string;
  study_id: string;
  subject_id: string;
  created_at: string;
  mrn?: string;
  date_offset_days?: number | null;
}

export interface PatientBulkRevealResponse {
  study_id: string;
  count: number;
  patients: PatientMapping[];
}

export interface DatasetManifest {
  id: string;
  study_id: string;
  global_hash_key_id: string;
  global_key_version: number;
  dataset_type: string;
  description: string | null;
  record_count: number | null;
  metadata_json: Record<string, unknown> | null;
  status: "pending" | "approved";
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
}

export interface AccessionMapping {
  id: string;
  patient_mapping_id: string;
  study_id: string;
  dataset_manifest_id: string;
  created_at: string;
  accession_number?: string;
  subject_id?: string;
}

export interface AccessionBulkRevealResponse {
  study_id: string;
  count: number;
  accessions: AccessionMapping[];
}

export interface DatasetUploadResponse {
  manifest: DatasetManifest;
  patients_created: number;
  patients_reused: number;
  accessions_created: number;
}

export interface ReidentificationRequest {
  id: string;
  study_id: string;
  requested_by: string;
  message: string;
  status: "pending" | "completed" | "denied";
  created_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
}

export const api = {
  listStudies: () => request<Study[]>("/api/v1/studies"),
  listExpiringStudies: () => request<Study[]>("/api/v1/studies/expiring"),
  getStudy: (id: string) => request<Study>(`/api/v1/studies/${id}`),
  createStudy: (data: Partial<Study>) =>
    request<Study>("/api/v1/studies", { method: "POST", body: JSON.stringify(data) }),

  rejectStudy: (id: string) =>
    request<Study>(`/api/v1/studies/${id}/reject`, { method: "POST" }),

  listGlobalKeys: () => request<GlobalKey[]>("/api/v1/keys/global"),
  rotateGlobalKey: () =>
    request<GlobalKey>("/api/v1/keys/global/rotate", { method: "POST" }),

  listPatients: (studyId: string) =>
    request<PatientMapping[]>(`/api/v1/studies/${studyId}/patients`),
  addPatient: (studyId: string, data: { mrn: string; subject_id: string }) =>
    request<PatientMapping>(`/api/v1/studies/${studyId}/patients`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  revealPatient: (studyId: string, patientId: string) =>
    request<PatientMapping>(`/api/v1/studies/${studyId}/patients/${patientId}/reveal`),
  revealAllPatients: (studyId: string) =>
    request<PatientBulkRevealResponse>(`/api/v1/studies/${studyId}/patients/reveal-all`),

  listDatasets: (studyId: string) =>
    request<DatasetManifest[]>(`/api/v1/studies/${studyId}/datasets`),
  uploadDataset: (
    studyId: string,
    data: {
      dataset_type?: string;
      description?: string;
      records: Array<{ mrn: string; subject_id: string; accession_number: string }>;
    },
  ) =>
    request<DatasetUploadResponse>(`/api/v1/studies/${studyId}/datasets/upload`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  uploadDatasetCsv: async (
    studyId: string,
    file: File,
    datasetType?: string,
    description?: string,
  ): Promise<DatasetUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    if (datasetType) formData.append("dataset_type", datasetType);
    if (description) formData.append("description", description);
    const res = await fetch(`/api/v1/studies/${studyId}/datasets/upload-csv`, {
      method: "POST",
      headers: { "X-User-Role": currentRole },
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error((body as { detail?: string }).detail ?? res.statusText);
    }
    return res.json() as Promise<DatasetUploadResponse>;
  },

  approveDataset: (studyId: string, datasetId: string) =>
    request<DatasetManifest>(
      `/api/v1/studies/${studyId}/datasets/${datasetId}/approve`,
      { method: "POST" },
    ),

  listAccessions: (studyId: string, datasetId?: string) => {
    const params = datasetId ? `?dataset_id=${datasetId}` : "";
    return request<AccessionMapping[]>(
      `/api/v1/studies/${studyId}/accessions${params}`,
    );
  },
  revealAccession: (studyId: string, accessionId: string) =>
    request<AccessionMapping>(
      `/api/v1/studies/${studyId}/accessions/${accessionId}/reveal`,
    ),
  revealAllAccessions: (studyId: string, datasetId?: string) => {
    const params = datasetId ? `?dataset_id=${datasetId}` : "";
    return request<AccessionBulkRevealResponse>(
      `/api/v1/studies/${studyId}/accessions/reveal-all${params}`,
    );
  },

  listReidentificationRequests: (studyId: string) =>
    request<ReidentificationRequest[]>(
      `/api/v1/studies/${studyId}/reidentification-requests`,
    ),
  createReidentificationRequest: (studyId: string, message: string) =>
    request<ReidentificationRequest>(
      `/api/v1/studies/${studyId}/reidentification-requests`,
      { method: "POST", body: JSON.stringify({ message }) },
    ),
  resolveReidentificationRequest: (
    studyId: string,
    requestId: string,
    status: "completed" | "denied",
  ) =>
    request<ReidentificationRequest>(
      `/api/v1/studies/${studyId}/reidentification-requests/${requestId}/resolve`,
      { method: "POST", body: JSON.stringify({ status }) },
    ),
};
