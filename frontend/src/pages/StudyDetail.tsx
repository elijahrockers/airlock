import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, DatasetManifest, PatientMapping, Study } from "../api/client";
import DataTable from "../components/DataTable";
import StatusBadge from "../components/StatusBadge";

export default function StudyDetail() {
  const { id } = useParams<{ id: string }>();
  const [study, setStudy] = useState<Study | null>(null);
  const [patients, setPatients] = useState<PatientMapping[]>([]);
  const [datasets, setDatasets] = useState<DatasetManifest[]>([]);

  useEffect(() => {
    if (!id) return;
    api.getStudy(id).then(setStudy);
    api.listPatients(id).then(setPatients);
    api.listDatasets(id).then(setDatasets);
  }, [id]);

  if (!study) return <p className="text-gray-500">Loading...</p>;

  return (
    <div className="space-y-8">
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

      <section>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">
          Patient Mappings ({patients.length})
        </h2>
        <DataTable
          columns={[
            { key: "subject", header: "Subject ID", render: (p: PatientMapping) => p.subject_id },
            {
              key: "created",
              header: "Added",
              render: (p: PatientMapping) => new Date(p.created_at).toLocaleDateString(),
            },
          ]}
          data={patients}
        />
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">
          Dataset Manifests ({datasets.length})
        </h2>
        <DataTable
          columns={[
            { key: "type", header: "Type", render: (d: DatasetManifest) => d.dataset_type },
            {
              key: "desc",
              header: "Description",
              render: (d: DatasetManifest) => d.description ?? "—",
            },
            {
              key: "records",
              header: "Records",
              render: (d: DatasetManifest) => d.record_count?.toLocaleString() ?? "—",
            },
            {
              key: "keyver",
              header: "Key Version",
              render: (d: DatasetManifest) => `v${d.global_key_version}`,
            },
            {
              key: "created",
              header: "Created",
              render: (d: DatasetManifest) => new Date(d.created_at).toLocaleDateString(),
            },
          ]}
          data={datasets}
        />
      </section>
    </div>
  );
}
