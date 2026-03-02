const BASE = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface Study {
  id: string;
  irb_pro_number: string;
  title: string;
  description: string | null;
  pi_name: string;
  requestor: string | null;
  status: "draft" | "active" | "completed" | "archived";
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
}

export interface DatasetManifest {
  id: string;
  study_id: string;
  global_key_version: number;
  dataset_type: string;
  description: string | null;
  record_count: number | null;
  created_at: string;
}

export const api = {
  listStudies: () => request<Study[]>("/api/v1/studies"),
  getStudy: (id: string) => request<Study>(`/api/v1/studies/${id}`),
  createStudy: (data: Partial<Study>) =>
    request<Study>("/api/v1/studies", { method: "POST", body: JSON.stringify(data) }),

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

  listDatasets: (studyId: string) =>
    request<DatasetManifest[]>(`/api/v1/studies/${studyId}/datasets`),
};
