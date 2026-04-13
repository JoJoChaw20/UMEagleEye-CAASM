import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Mock trend data for 7 days
const TREND_DATA = [
  { date: "Mon", assets: 5, criticalAssets: 1 },
  { date: "Tue", assets: 8, criticalAssets: 2 },
  { date: "Wed", assets: 12, criticalAssets: 3 },
  { date: "Thu", assets: 15, criticalAssets: 4 },
  { date: "Fri", assets: 18, criticalAssets: 5 },
  { date: "Sat", assets: 20, criticalAssets: 5 },
  { date: "Sun", assets: 22, criticalAssets: 6 },
];

const DEVICE_TYPES_COLORS = {
  "Server": "#ef4444",
  "Workstation": "#3b82f6",
  "Network Device": "#8b5cf6",
  "Printer": "#10b981",
  "Unknown Device": "#6b7280",
};

function StatCard({ title, value, subtext, color = "slate" }) {
  const colorMap = {
    slate: "bg-slate-100 text-slate-900",
    red: "bg-red-100 text-red-900",
    blue: "bg-blue-100 text-blue-900",
    purple: "bg-purple-100 text-purple-900",
  };

  return (
    <div className={`${colorMap[color]} rounded-lg p-6`}>
      <p className="text-sm font-medium opacity-80">{title}</p>
      <p className="mt-2 text-3xl font-bold">{value}</p>
      {subtext && <p className="mt-1 text-xs opacity-75">{subtext}</p>}
    </div>
  );
}

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

  // Calculate statistics
  const totalAssets = assets.length;
  const criticalAssets = assets.filter((a) => a.criticality_score >= 8).length;
  const avgCriticality =
    assets.length > 0
      ? (assets.reduce((sum, a) => sum + a.criticality_score, 0) / assets.length).toFixed(1)
      : 0;

  // Device type distribution
  const deviceTypeDistribution = assets.reduce((acc, asset) => {
    const existing = acc.find((d) => d.name === asset.device_type);
    if (existing) {
      existing.value += 1;
    } else {
      acc.push({ name: asset.device_type, value: 1 });
    }
    return acc;
  }, []);

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 px-4 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-7xl">
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-4xl font-bold tracking-tight text-slate-900">
            UMEagleEye Executive Dashboard
          </h1>
          <p className="mt-2 text-lg text-slate-600">
            Real-time asset discovery and infrastructure monitoring
          </p>
        </header>

        {/* Error State */}
        {error && (
          <div className="mb-6 rounded-lg border border-red-300 bg-red-50 px-6 py-4 text-red-700">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-slate-600">Loading dashboard...</p>
          </div>
        ) : (
          <>
            {/* Key Metrics */}
            <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-4">
              <StatCard title="Total Assets" value={totalAssets} color="slate" />
              <StatCard
                title="Critical Assets"
                value={criticalAssets}
                subtext="Score ≥ 8"
                color="red"
              />
              <StatCard
                title="Average Criticality"
                value={avgCriticality}
                subtext="Out of 10"
                color="blue"
              />
              <StatCard
                title="Last Updated"
                value="Just now"
                subtext={new Date().toLocaleTimeString()}
                color="purple"
              />
            </div>

            {/* Charts Row */}
            <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
              {/* Asset Growth Trend */}
              <div className="col-span-2 rounded-lg bg-white p-6 shadow">
                <h2 className="mb-4 text-lg font-semibold text-slate-900">
                  Asset Discovery Trend
                </h2>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={TREND_DATA}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="assets"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      name="Total Assets"
                    />
                    <Line
                      type="monotone"
                      dataKey="criticalAssets"
                      stroke="#ef4444"
                      strokeWidth={2}
                      name="Critical Assets"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Device Type Distribution */}
              <div className="rounded-lg bg-white p-6 shadow">
                <h2 className="mb-4 text-lg font-semibold text-slate-900">
                  Device Distribution
                </h2>
                {deviceTypeDistribution.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={deviceTypeDistribution}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={(entry) => `${entry.name}: ${entry.value}`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {deviceTypeDistribution.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={
                              DEVICE_TYPES_COLORS[entry.name] ||
                              `hsl(${(index * 360) / deviceTypeDistribution.length}, 70%, 50%)`
                            }
                          />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="py-8 text-center text-slate-500">No device data</p>
                )}
              </div>
            </div>

            {/* Asset Inventory Table */}
            <div className="rounded-lg bg-white p-6 shadow">
              <h2 className="mb-4 text-lg font-semibold text-slate-900">Asset Inventory</h2>
              {assets.length === 0 ? (
                <p className="py-8 text-center text-slate-500">
                  No assets discovered yet. Run a network scan to populate this table.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b border-slate-200 bg-slate-50">
                      <tr>
                        <th className="px-4 py-3 text-left font-semibold text-slate-700">
                          Hostname
                        </th>
                        <th className="px-4 py-3 text-left font-semibold text-slate-700">
                          IP Address
                        </th>
                        <th className="px-4 py-3 text-left font-semibold text-slate-700">Owner</th>
                        <th className="px-4 py-3 text-left font-semibold text-slate-700">
                          Device Type
                        </th>
                        <th className="px-4 py-3 text-left font-semibold text-slate-700">OS</th>
                        <th className="px-4 py-3 text-center font-semibold text-slate-700">
                          Criticality
                        </th>
                        <th className="px-4 py-3 text-center font-semibold text-slate-700">
                          Last Scanned
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {assets.map((asset) => (
                        <tr key={asset.asset_id} className="hover:bg-slate-50">
                          <td className="px-4 py-3 font-medium text-slate-900">
                            {asset.hostname}
                          </td>
                          <td className="px-4 py-3 text-slate-600">{asset.ip_address}</td>
                          <td className="px-4 py-3 text-slate-600">{asset.owner}</td>
                          <td className="px-4 py-3 text-slate-600">{asset.device_type}</td>
                          <td className="px-4 py-3 text-slate-600">{asset.os_info}</td>
                          <td className="px-4 py-3 text-center">
                            <span
                              className={`inline-flex items-center justify-center rounded-full px-3 py-1 text-xs font-semibold text-white ${
                                asset.criticality_score >= 8
                                  ? "bg-red-500"
                                  : asset.criticality_score >= 6
                                    ? "bg-yellow-500"
                                    : "bg-green-500"
                              }`}
                            >
                              {asset.criticality_score}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center text-slate-600">
                            {new Date(asset.last_scanned).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </main>
  );
}

export default App;
