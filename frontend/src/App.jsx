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
  const [driftEvents, setDriftEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function loadDashboardData({ silent = false } = {}) {
    try {
      if (silent) {
        setIsRefreshing(true);
      } else {
        setLoading(true);
      }

      const [assetsResponse, driftResponse] = await Promise.all([
        fetch(`${API_BASE}/assets`),
        fetch(`${API_BASE}/drift-events`),
      ]);

      if (!assetsResponse.ok) {
        throw new Error(`Asset request failed with status ${assetsResponse.status}`);
      }

      if (!driftResponse.ok) {
        throw new Error(`Drift request failed with status ${driftResponse.status}`);
      }

      const [assetData, driftData] = await Promise.all([
        assetsResponse.json(),
        driftResponse.json(),
      ]);

      setAssets(assetData);
      setDriftEvents(driftData);
      setError("");
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Failed to fetch assets");
    } finally {
      if (silent) {
        setIsRefreshing(false);
      } else {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    loadDashboardData();

    const intervalId = setInterval(async () => {
      loadDashboardData({ silent: true });
    }, 10000);

    return () => clearInterval(intervalId);
  }, []);

  // Calculate statistics
  const totalAssets = assets.length;
  const criticalAssets = assets.filter((a) => a.criticality_score >= 8).length;
  const avgCriticality =
    assets.length > 0
      ? (assets.reduce((sum, a) => sum + a.criticality_score, 0) / assets.length).toFixed(1)
      : 0;

  const scannedIps = [...new Set(assets.map((asset) => asset.ip_address))];
  const hasDriftEvents = driftEvents.length > 0;

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
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-slate-900">
                UMEagleEye Executive Dashboard
              </h1>
              <p className="mt-2 text-lg text-slate-600">
                Real-time asset discovery and infrastructure monitoring
              </p>
            </div>
            <button
              type="button"
              onClick={loadDashboardData}
              className="inline-flex items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
            >
              {isRefreshing ? "Refreshing..." : "Refresh now"}
            </button>
          </div>
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
            <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
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
                title="Drift Events"
                value={driftEvents.length}
                subtext="Latest PORT_DRIFT results"
                color="purple"
              />
              <StatCard
                title="Last Updated"
                value="Just now"
                subtext={new Date().toLocaleTimeString()}
                color="slate"
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

            {/* Drift Detection Results */}
            <div className="mb-8 rounded-lg bg-white p-6 shadow">
              <div className="mb-4 flex items-center justify-between gap-4">
                <h2 className="text-lg font-semibold text-slate-900">
                  Recent Drift Detection Results
                </h2>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                  {driftEvents.length} event{driftEvents.length === 1 ? "" : "s"}
                </span>
              </div>

              {!hasDriftEvents ? (
                <p className="text-sm text-slate-500">
                  No drift events recorded yet. Run the scheduled job or execute drift detection manually to populate this section.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b border-slate-200 bg-slate-50">
                      <tr>
                        <th className="px-4 py-3 text-left font-semibold text-slate-700">Asset</th>
                        <th className="px-4 py-3 text-left font-semibold text-slate-700">Type</th>
                        <th className="px-4 py-3 text-left font-semibold text-slate-700">New Ports</th>
                        <th className="px-4 py-3 text-left font-semibold text-slate-700">Closed Ports</th>
                        <th className="px-4 py-3 text-left font-semibold text-slate-700">Remediation</th>
                        <th className="px-4 py-3 text-center font-semibold text-slate-700">Severity</th>
                        <th className="px-4 py-3 text-center font-semibold text-slate-700">Time</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {driftEvents.map((event) => (
                        <tr key={event.event_id} className="hover:bg-slate-50">
                          <td className="px-4 py-3">
                            <div className="font-medium text-slate-900">{event.hostname}</div>
                            <div className="text-xs text-slate-500">{event.ip_address}</div>
                          </td>
                          <td className="px-4 py-3 text-slate-600">{event.drift_type}</td>
                          <td className="px-4 py-3 text-slate-600">
                            {event.new_ports.length > 0
                              ? event.new_ports.map((port) => port.port).join(", ")
                              : "-"}
                          </td>
                          <td className="px-4 py-3 text-slate-600">
                            {event.closed_ports.length > 0
                              ? event.closed_ports.map((port) => port.port ?? port).join(", ")
                              : "-"}
                          </td>
                          <td className="max-w-xl px-4 py-3 text-slate-600">
                            {event.remediation ? (
                              <details>
                                <summary className="cursor-pointer text-xs font-semibold text-slate-700">
                                  View guidance
                                </summary>
                                <pre className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-slate-600">
                                  {event.remediation}
                                </pre>
                              </details>
                            ) : (
                              <span className="text-xs text-slate-400">No guidance generated</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span
                              className={`inline-flex items-center justify-center rounded-full px-3 py-1 text-xs font-semibold text-white ${
                                event.severity === "CRITICAL"
                                  ? "bg-red-500"
                                  : event.severity === "WARNING"
                                    ? "bg-yellow-500"
                                    : "bg-slate-500"
                              }`}
                            >
                              {event.severity}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center text-slate-600">
                            {new Date(event.timestamp).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Asset Inventory Table */}
            <div className="rounded-lg bg-white p-6 shadow">
              <h2 className="mb-4 text-lg font-semibold text-slate-900">Scanned IP Addresses</h2>
              {scannedIps.length === 0 ? (
                <p className="mb-6 text-sm text-slate-500">No scanned IP addresses yet.</p>
              ) : (
                <div className="mb-6 flex flex-wrap gap-2">
                  {scannedIps.map((ip) => (
                    <span
                      key={ip}
                      className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800"
                    >
                      {ip}
                    </span>
                  ))}
                </div>
              )}

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
