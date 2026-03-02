import { useEffect, useState } from "react";
import { api, GlobalKey } from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import DataTable from "../components/DataTable";

export default function KeyManagement() {
  const [keys, setKeys] = useState<GlobalKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showRotate, setShowRotate] = useState(false);

  const load = () => {
    setLoading(true);
    api.listGlobalKeys().then(setKeys).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const rotate = async () => {
    await api.rotateGlobalKey();
    setShowRotate(false);
    load();
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Global Hash Keys</h1>
        <button
          onClick={() => setShowRotate(true)}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Rotate Key
        </button>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <DataTable
          columns={[
            { key: "version", header: "Version", render: (k: GlobalKey) => `v${k.version}` },
            {
              key: "active",
              header: "Active",
              render: (k: GlobalKey) => (
                <span
                  className={`inline-flex h-2 w-2 rounded-full ${
                    k.is_active ? "bg-green-500" : "bg-gray-300"
                  }`}
                />
              ),
            },
            {
              key: "created",
              header: "Created",
              render: (k: GlobalKey) => new Date(k.created_at).toLocaleString(),
            },
            {
              key: "retired",
              header: "Retired",
              render: (k: GlobalKey) =>
                k.retired_at ? new Date(k.retired_at).toLocaleString() : "—",
            },
          ]}
          data={keys}
        />
      )}

      <ConfirmDialog
        open={showRotate}
        title="Rotate Global Key"
        message="This will retire the current active key and create a new version. Existing datasets will keep their original key version. Continue?"
        onConfirm={rotate}
        onCancel={() => setShowRotate(false)}
      />
    </div>
  );
}
