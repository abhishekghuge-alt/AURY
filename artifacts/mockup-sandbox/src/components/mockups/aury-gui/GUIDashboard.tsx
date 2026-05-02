import { useState, useEffect } from "react";
import { Download, History, Settings, BarChart2, Database, X, ChevronDown, Play, Pause, Trash2, FolderOpen, Clipboard, Search, Moon, Sun, Youtube, Music, FileVideo, Zap } from "lucide-react";

type Tab = "dashboard" | "history" | "analytics" | "settings" | "dbreport";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: Download },
  { id: "history", label: "History", icon: History },
  { id: "analytics", label: "Analytics", icon: BarChart2 },
  { id: "settings", label: "Settings", icon: Settings },
  { id: "dbreport", label: "DB Report", icon: Database },
] as const;

const queueItems = [
  { id: 1, title: "Lofi Hip Hop Radio – Beats to Relax", platform: "YouTube", quality: "1080p", progress: 68, speed: "14.2 MB/s", eta: "0:38", status: "downloading" },
  { id: 2, title: "Kendrick Lamar – Not Like Us (Official)", platform: "YouTube", quality: "MP3", progress: 100, speed: "—", eta: "Done", status: "done" },
  { id: 3, title: "4K Nature Timelapse – Mountains", platform: "YouTube", quality: "4K", progress: 0, speed: "—", eta: "Queued", status: "queued" },
];

const historyRows = [
  { title: "Lofi Hip Hop Mix", platform: "YouTube", quality: "1080p", size: "1.2 GB", date: "May 1, 2026", status: "success" },
  { title: "Not Like Us – Kendrick", platform: "YouTube", quality: "MP3", size: "8.4 MB", date: "May 1, 2026", status: "success" },
  { title: "4K Nature Documentary", platform: "YouTube", quality: "4K", size: "4.1 GB", date: "Apr 30, 2026", status: "success" },
  { title: "Study With Me – 3 Hours", platform: "YouTube", quality: "720p", size: "680 MB", date: "Apr 29, 2026", status: "success" },
  { title: "Epic Soundtrack Collection", platform: "YouTube", quality: "MP3", size: "34 MB", date: "Apr 28, 2026", status: "success" },
];

const weeklyData = [18, 42, 30, 55, 38, 70, 24];
const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const maxVal = Math.max(...weeklyData);

function StatCard({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div className={`rounded-xl p-4 border ${color}`}>
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      <div className="text-xs text-gray-500">{sub}</div>
    </div>
  );
}

function ProgressBar({ pct, status }: { pct: number; status: string }) {
  const color = status === "done" ? "bg-green-500" : status === "queued" ? "bg-gray-600" : "bg-blue-500";
  return (
    <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
      <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function GUIDashboard() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [dark, setDark] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [quality, setQuality] = useState("1080p");
  const [liveProgress, setLiveProgress] = useState(68);

  useEffect(() => {
    const t = setInterval(() => setLiveProgress(p => p >= 99 ? 68 : p + 0.4), 300);
    return () => clearInterval(t);
  }, []);

  const bg = dark ? "bg-[#0d1117]" : "bg-gray-100";
  const sidebar = dark ? "bg-[#161b22] border-[#30363d]" : "bg-white border-gray-200";
  const card = dark ? "bg-[#161b22] border-[#30363d]" : "bg-white border-gray-200";
  const text = dark ? "text-gray-200" : "text-gray-800";
  const muted = dark ? "text-gray-500" : "text-gray-500";

  return (
    <div className={`min-h-screen ${bg} ${text} font-sans flex flex-col`}>
      {/* Title bar */}
      <div className={`flex items-center justify-between px-4 py-2 border-b ${dark ? "bg-[#161b22] border-[#30363d]" : "bg-white border-gray-200"}`}>
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
            <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
            <div className="w-3 h-3 rounded-full bg-[#28c840]" />
          </div>
          <span className="text-sm font-semibold">AURY — Smart Media Downloader</span>
          <span className={`text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400`}>V2 GUI</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setDark(!dark)} className="p-1.5 rounded hover:bg-white/10 transition-colors">
            {dark ? <Sun className="w-4 h-4 text-yellow-400" /> : <Moon className="w-4 h-4 text-gray-600" />}
          </button>
          <button onClick={() => setShowModal(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg transition-colors">
            <Download className="w-3.5 h-3.5" /> New Download
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className={`w-48 border-r ${sidebar} flex flex-col py-3 shrink-0`}>
          {navItems.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id as Tab)}
              className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors text-left ${
                tab === id
                  ? "bg-blue-600/20 text-blue-400 border-r-2 border-blue-500"
                  : `${muted} hover:bg-white/5`
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
          <div className="mt-auto px-4 py-3 border-t border-[#30363d]">
            <div className={`text-xs ${muted}`}>
              <div>1 active · 3 total</div>
              <div className="mt-1 text-green-400">● Connected</div>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 overflow-y-auto p-5">

          {tab === "dashboard" && (
            <div>
              <div className="text-lg font-bold mb-4">Dashboard</div>
              {/* Stats row */}
              <div className="grid grid-cols-4 gap-3 mb-5">
                <StatCard label="Total Downloads" value="3" sub="All time" color={`border-blue-500/30 bg-blue-500/5`} />
                <StatCard label="Data Saved" value="21 MB" sub="This session" color={`border-green-500/30 bg-green-500/5`} />
                <StatCard label="Sessions" value="4" sub="Lifetime" color={`border-purple-500/30 bg-purple-500/5`} />
                <StatCard label="Active" value="1" sub="Downloading now" color={`border-orange-500/30 bg-orange-500/5`} />
              </div>
              {/* Queue */}
              <div className={`rounded-xl border ${card} p-4`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="font-semibold text-sm">Download Queue</div>
                  <div className="flex gap-2">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400">1 active</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">1 done</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-500/20 text-gray-400">1 queued</span>
                  </div>
                </div>
                <div className="space-y-3">
                  {queueItems.map(item => (
                    <div key={item.id} className={`rounded-lg p-3 ${dark ? "bg-[#0d1117]" : "bg-gray-50"}`}>
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <div className="text-sm font-medium truncate max-w-[340px]">{item.title}</div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs text-red-400 flex items-center gap-1"><Youtube className="w-3 h-3" />{item.platform}</span>
                            <span className={`text-xs px-1.5 py-0.5 rounded ${dark ? "bg-gray-700" : "bg-gray-200"}`}>{item.quality}</span>
                            {item.status === "downloading" && (
                              <span className="text-xs text-blue-400">⚡ {item.speed} · ETA {item.eta}</span>
                            )}
                            {item.status === "done" && <span className="text-xs text-green-400">✓ Complete</span>}
                            {item.status === "queued" && <span className="text-xs text-gray-500">⏳ Queued</span>}
                          </div>
                        </div>
                        <div className="flex gap-1">
                          {item.status === "downloading" && <button className="p-1 rounded hover:bg-white/10"><Pause className="w-3 h-3 text-yellow-400" /></button>}
                          {item.status === "queued" && <button className="p-1 rounded hover:bg-white/10"><Play className="w-3 h-3 text-green-400" /></button>}
                          {item.status === "done" && <button className="p-1 rounded hover:bg-white/10"><FolderOpen className="w-3 h-3 text-gray-400" /></button>}
                          <button className="p-1 rounded hover:bg-white/10"><Trash2 className="w-3 h-3 text-red-400" /></button>
                        </div>
                      </div>
                      <ProgressBar pct={item.id === 1 ? liveProgress : item.progress} status={item.status} />
                      {item.id === 1 && (
                        <div className="text-xs text-gray-500 mt-1">{Math.floor(liveProgress)}%</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab === "history" && (
            <div>
              <div className="text-lg font-bold mb-4">Download History</div>
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${card} mb-4 w-72`}>
                <Search className="w-4 h-4 text-gray-500" />
                <input className={`bg-transparent outline-none text-sm flex-1 ${text}`} placeholder="Search history…" />
              </div>
              <div className={`rounded-xl border ${card} overflow-hidden`}>
                <table className="w-full text-sm">
                  <thead>
                    <tr className={`border-b ${dark ? "border-[#30363d] bg-[#0d1117]" : "border-gray-200 bg-gray-50"}`}>
                      {["Title", "Platform", "Quality", "Size", "Date", "Status"].map(h => (
                        <th key={h} className={`text-left px-4 py-2.5 text-xs font-semibold ${muted}`}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {historyRows.map((r, i) => (
                      <tr key={i} className={`border-b ${dark ? "border-[#30363d] hover:bg-white/5" : "border-gray-100 hover:bg-gray-50"} transition-colors cursor-pointer`}>
                        <td className="px-4 py-3 font-medium max-w-[200px] truncate">{r.title}</td>
                        <td className="px-4 py-3 text-red-400 text-xs flex items-center gap-1 mt-2"><Youtube className="w-3 h-3" />{r.platform}</td>
                        <td className="px-4 py-3"><span className={`text-xs px-2 py-0.5 rounded ${dark ? "bg-gray-700" : "bg-gray-200"}`}>{r.quality}</span></td>
                        <td className="px-4 py-3 text-xs text-gray-400">{r.size}</td>
                        <td className="px-4 py-3 text-xs text-gray-400">{r.date}</td>
                        <td className="px-4 py-3"><span className="text-xs text-green-400">✓</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {tab === "analytics" && (
            <div>
              <div className="text-lg font-bold mb-4">Analytics</div>
              <div className="grid grid-cols-2 gap-4 mb-5">
                <div className={`rounded-xl border ${card} p-4`}>
                  <div className="text-sm font-semibold mb-3">Downloads This Week</div>
                  <div className="flex items-end gap-2 h-32">
                    {weeklyData.map((v, i) => (
                      <div key={i} className="flex flex-col items-center flex-1 gap-1">
                        <div className="text-xs text-gray-500">{v}</div>
                        <div className="w-full bg-blue-500 rounded-t transition-all" style={{ height: `${(v / maxVal) * 80}px` }} />
                        <div className="text-xs text-gray-500">{days[i]}</div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className={`rounded-xl border ${card} p-4`}>
                  <div className="text-sm font-semibold mb-3">Quality Split</div>
                  <div className="space-y-2">
                    {[["4K / 2160p", "8%", "bg-purple-500"], ["1080p FHD", "52%", "bg-blue-500"], ["720p HD", "24%", "bg-green-500"], ["MP3 Audio", "16%", "bg-orange-400"]].map(([l, p, c]) => (
                      <div key={l} className="flex items-center gap-2 text-xs">
                        <div className={`w-2 h-2 rounded-full ${c}`} />
                        <span className="text-gray-400 w-24">{l}</span>
                        <div className="flex-1 h-1.5 bg-gray-700 rounded-full">
                          <div className={`h-full rounded-full ${c}`} style={{ width: p }} />
                        </div>
                        <span className="text-gray-400 w-8 text-right">{p}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className={`rounded-xl border ${card} p-4`}>
                <div className="text-sm font-semibold mb-3">Platform Split</div>
                <div className="flex gap-4">
                  {[["YouTube", "84%", "text-red-400"], ["SoundCloud", "9%", "text-orange-400"], ["Vimeo", "4%", "text-blue-400"], ["Other", "3%", "text-gray-400"]].map(([l, p, c]) => (
                    <div key={l} className="flex flex-col items-center flex-1">
                      <div className={`text-2xl font-bold ${c}`}>{p}</div>
                      <div className="text-xs text-gray-500 mt-1">{l}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab === "settings" && (
            <div>
              <div className="text-lg font-bold mb-4">Settings</div>
              <div className={`rounded-xl border ${card} divide-y ${dark ? "divide-[#30363d]" : "divide-gray-100"}`}>
                {[
                  ["Output Folder", "~/Downloads/AURY", "folder"],
                  ["Default Quality", "1080p FHD", "dropdown"],
                  ["Audio Format", "MP3 320kbps", "dropdown"],
                  ["Max Workers", "4", "number"],
                  ["Turbo Mode (aria2c)", "Enabled", "toggle-on"],
                  ["Auto-Subtitles", "Disabled", "toggle-off"],
                  ["Clipboard Watch", "Enabled", "toggle-on"],
                  ["Theme", "Dark", "toggle-on"],
                ].map(([k, v, type]) => (
                  <div key={k} className="flex items-center justify-between px-5 py-3">
                    <div>
                      <div className="text-sm font-medium">{k}</div>
                    </div>
                    {type === "toggle-on" && (
                      <div className="w-10 h-5 bg-blue-500 rounded-full relative cursor-pointer">
                        <div className="absolute right-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow" />
                      </div>
                    )}
                    {type === "toggle-off" && (
                      <div className="w-10 h-5 bg-gray-600 rounded-full relative cursor-pointer">
                        <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow" />
                      </div>
                    )}
                    {(type === "folder" || type === "dropdown" || type === "number") && (
                      <span className={`text-sm ${muted} flex items-center gap-1`}>{v} {type === "dropdown" && <ChevronDown className="w-3 h-3" />}</span>
                    )}
                  </div>
                ))}
              </div>
              <button className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors">Save Settings</button>
            </div>
          )}

          {tab === "dbreport" && (
            <div>
              <div className="text-lg font-bold mb-4">DB Report</div>
              <div className="grid grid-cols-3 gap-3 mb-4">
                {[["Total Downloads", "3"], ["Sessions", "4"], ["DB Size", "72 KB"]].map(([l, v]) => (
                  <div key={l} className={`rounded-xl border ${card} p-4`}>
                    <div className={`text-xs ${muted} mb-1`}>{l}</div>
                    <div className="text-xl font-bold">{v}</div>
                  </div>
                ))}
              </div>
              <div className={`rounded-xl border ${card} p-4 mb-4`}>
                <div className="text-sm font-semibold mb-2">SQL Runner</div>
                <textarea className={`w-full h-20 rounded-lg p-3 text-sm font-mono outline-none border resize-none ${dark ? "bg-[#0d1117] border-[#30363d] text-green-400" : "bg-gray-50 border-gray-200 text-gray-800"}`} defaultValue="SELECT platform, COUNT(*) as count FROM downloads GROUP BY platform;" />
                <button className="mt-2 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs rounded-lg">Run Query</button>
              </div>
              <div className={`rounded-xl border ${card} overflow-hidden`}>
                <table className="w-full text-xs">
                  <thead><tr className={`border-b ${dark ? "border-[#30363d] bg-[#0d1117]" : "border-gray-200 bg-gray-50"}`}>
                    {["platform", "count"].map(h => <th key={h} className={`text-left px-4 py-2 ${muted} font-semibold`}>{h}</th>)}
                  </tr></thead>
                  <tbody>
                    <tr className={`border-b ${dark ? "border-[#30363d]" : "border-gray-100"}`}>
                      <td className="px-4 py-2 text-red-400">YouTube</td><td className="px-4 py-2">3</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Download Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className={`w-[480px] rounded-2xl border shadow-2xl p-6 ${dark ? "bg-[#161b22] border-[#30363d]" : "bg-white border-gray-200"}`}>
            <div className="flex items-center justify-between mb-4">
              <div className="font-bold text-base">New Download</div>
              <button onClick={() => setShowModal(false)}><X className="w-4 h-4 text-gray-500 hover:text-white" /></button>
            </div>
            <div className="mb-3">
              <label className={`text-xs ${muted} mb-1 block`}>URL</label>
              <div className={`flex items-center gap-2 rounded-lg border px-3 py-2 ${dark ? "bg-[#0d1117] border-[#30363d]" : "bg-gray-50 border-gray-200"}`}>
                <input className="bg-transparent outline-none flex-1 text-sm" placeholder="https://youtube.com/watch?v=…" value={urlInput} onChange={e => setUrlInput(e.target.value)} autoFocus />
                <button title="Paste"><Clipboard className="w-4 h-4 text-gray-500 hover:text-blue-400 cursor-pointer" /></button>
              </div>
            </div>
            {/* Thumbnail placeholder */}
            <div className={`rounded-lg mb-3 h-28 flex items-center justify-center ${dark ? "bg-[#0d1117]" : "bg-gray-100"} border ${dark ? "border-[#30363d]" : "border-gray-200"}`}>
              <div className="text-center">
                <FileVideo className="w-8 h-8 text-gray-600 mx-auto mb-1" />
                <div className="text-xs text-gray-500">Thumbnail preview</div>
              </div>
            </div>
            <div className="mb-4">
              <label className={`text-xs ${muted} mb-1 block`}>Quality</label>
              <div className="grid grid-cols-4 gap-2">
                {["4K", "1080p", "720p", "MP3"].map(q => (
                  <button key={q} onClick={() => setQuality(q)} className={`py-1.5 rounded-lg text-xs font-medium border transition-colors ${quality === q ? "bg-blue-600 border-blue-500 text-white" : `border-[#30363d] ${muted} hover:border-blue-500`}`}>{q}</button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setShowModal(false)} className={`flex-1 py-2 rounded-lg text-sm border ${dark ? "border-[#30363d]" : "border-gray-200"} ${muted} hover:bg-white/5 transition-colors`}>Cancel</button>
              <button onClick={() => setShowModal(false)} className="flex-1 py-2 rounded-lg text-sm bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors flex items-center justify-center gap-2">
                <Zap className="w-4 h-4" /> Start Download
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
