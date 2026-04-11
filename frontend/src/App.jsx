import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function App() {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadAssets() {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE}/assets`);
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        const data = await response.json();
        setAssets(data);
      } catch (fetchError) {
        setError(fetchError instanceof Error ? fetchError.message : "Failed to fetch assets");
      } finally {
        setLoading(false);
      }
    }

    loadAssets();
  }, []);

  return (
    <main className="min-h-screen px-4 py-10 sm:px-8">
      <div className="mx-auto w-full max-w-6xl rounded-2xl bg-white p-6 shadow-lg sm:p-8">
        <header className="mb-6 border-b border-slate-200 pb-4">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">UMEagleEye Assets</h1>
          <p className="mt-1 text-sm text-slate-500">Live data from FastAPI and PostgreSQL mock seed records.</p>
        </header>

        {loading && <p className="text-slate-600">Loading assets...</p>}

        {error && (
          <div className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 font-semibold text-slate-700">Hostname</th>
                  <th className="px-4 py-3 font-semibold text-slate-700">IP Address</th>
                  <th className="px-4 py-3 font-semibold text-slate-700">Owner</th>
                  <th className="px-4 py-3 font-semibold text-slate-700">Device Type</th>
                  <th className="px-4 py-3 font-semibold text-slate-700">OS</th>
                  <th className="px-4 py-3 font-semibold text-slate-700">Criticality</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {assets.map((asset) => (
                  <tr key={asset.asset_id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-800">{asset.hostname}</td>
                    <td className="px-4 py-3 text-slate-600">{asset.ip_address}</td>
                    <td className="px-4 py-3 text-slate-600">{asset.owner}</td>
                    <td className="px-4 py-3 text-slate-600">{asset.device_type}</td>
                    <td className="px-4 py-3 text-slate-600">{asset.os_info}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-slate-900 px-2.5 py-1 text-xs font-semibold text-white">
                        {asset.criticality_score}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}

export default App;
