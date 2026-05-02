import { useState, useEffect } from "react";

const DOMAIN = "5e8260ec-caad-449d-835a-e57ca671057b-00-3ncomalnvm40h.pike.replit.dev";

type Screen = "menu" | "download" | "history" | "settings" | "quick";

const historyData = [
  { id: 1, title: "Lofi Hip Hop Mix – 2 Hours", platform: "YouTube", quality: "1080p", size: "1.2 GB", date: "2026-05-01", status: "✅" },
  { id: 2, title: "Kendrick Lamar – Not Like Us", platform: "YouTube", quality: "MP3", size: "8.4 MB", date: "2026-05-01", status: "✅" },
  { id: 3, title: "Nature Documentary 4K", platform: "YouTube", quality: "4K", size: "4.1 GB", date: "2026-04-30", status: "✅" },
];

const settingsData = [
  ["Output Folder", "~/Downloads/AURY"],
  ["Default Quality", "1080p"],
  ["Audio Format", "MP3 320kbps"],
  ["Max Workers", "4"],
  ["Turbo Mode (aria2c)", "Enabled"],
  ["Auto-Subtitles", "Disabled"],
  ["Clip Watch", "Enabled"],
  ["Theme", "Dark"],
];

export function CLITerminal() {
  const [screen, setScreen] = useState<Screen>("menu");
  const [inputLine, setInputLine] = useState("");
  const [dlUrl, setDlUrl] = useState("");
  const [dlQuality, setDlQuality] = useState("");
  const [dlStep, setDlStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [downloading, setDownloading] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (downloading) {
      setProgress(0);
      setDone(false);
      const interval = setInterval(() => {
        setProgress((p) => {
          if (p >= 100) {
            clearInterval(interval);
            setDownloading(false);
            setDone(true);
            return 100;
          }
          return p + Math.random() * 8;
        });
      }, 180);
      return () => clearInterval(interval);
    }
  }, [downloading]);

  const bar = (pct: number) => {
    const filled = Math.floor((pct / 100) * 30);
    return "█".repeat(filled) + "░".repeat(30 - filled);
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      const v = inputLine.trim();
      setInputLine("");
      if (screen === "menu") {
        if (v === "1") { setScreen("download"); setDlStep(1); }
        else if (v === "2") { setScreen("quick"); }
        else if (v === "3") setScreen("history");
        else if (v === "4") setScreen("settings");
        else if (v === "5" || v.toLowerCase() === "q") setScreen("menu");
      } else if (screen === "download") {
        if (dlStep === 1) { setDlUrl(v || "https://youtube.com/watch?v=dQw4w9WgXcQ"); setDlStep(2); }
        else if (dlStep === 2) { setDlQuality(v || "1080p"); setDlStep(3); setDownloading(true); }
        else if (dlStep === 3 && done) { setScreen("menu"); setDlStep(0); setDlUrl(""); setDlQuality(""); setDone(false); }
      } else if (screen === "quick") {
        if (v) { setDlUrl(v); setDlStep(3); setDlQuality("Best"); setDownloading(true); setScreen("download"); }
        else setScreen("menu");
      } else {
        if (v.toLowerCase() === "b" || v === "") setScreen("menu");
      }
    }
  };

  return (
    <div
      className="min-h-screen bg-[#0d1117] flex items-center justify-center p-4 font-mono"
      onClick={(e) => (e.currentTarget.querySelector("input") as HTMLInputElement)?.focus()}
    >
      <div className="w-[860px] bg-[#0d1117] rounded-xl overflow-hidden shadow-2xl border border-[#30363d]">
        {/* Title bar */}
        <div className="flex items-center gap-2 px-4 py-3 bg-[#161b22] border-b border-[#30363d]">
          <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
          <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
          <div className="w-3 h-3 rounded-full bg-[#28c840]" />
          <span className="ml-4 text-[#8b949e] text-xs">AURY — Smart Media Downloader v1.0 — Python 3.12</span>
        </div>

        {/* Terminal body */}
        <div className="p-6 text-sm leading-relaxed min-h-[540px] flex flex-col">
          {/* Banner */}
          <pre className="text-[#3fb950] text-[10px] leading-tight mb-2 select-none">{`
 ██████╗  ██╗   ██╗ ██████╗  ██╗   ██╗
 ██╔═══██╗ ██║   ██║ ██╔══██╗ ╚██╗ ██╔╝
 ███████║  ██║   ██║ ██████╔╝  ╚████╔╝ 
 ██╔══██║  ██║   ██║ ██╔══██╗   ╚██╔╝  
 ██║  ██║  ╚██████╔╝ ██║  ██║    ██║   
 ╚═╝  ╚═╝   ╚═════╝  ╚═╝  ╚═╝    ╚═╝`}</pre>

          {screen === "menu" && (
            <>
              <div className="border border-[#238636] rounded px-4 py-1 mb-3 text-[#3fb950] text-xs">
                Smart Media Downloader | V1 CLI
              </div>
              <div className="text-[#8b949e] text-xs mb-4">
                📦 Lifetime: <span className="text-white">3 downloads</span> · <span className="text-white">0.02 GB</span> · <span className="text-white">4 sessions</span>
              </div>
              <div className="border border-[#30363d] rounded p-4 mb-4">
                <div className="text-[#e6edf3] mb-3 font-bold">AURY — Main Menu</div>
                <div className="space-y-1 text-[#e6edf3]">
                  <div><span className="text-[#58a6ff]">[1]</span>  ⬇  Start New Download</div>
                  <div><span className="text-[#58a6ff]">[2]</span>  ⚡  Quick Download</div>
                  <div><span className="text-[#58a6ff]">[3]</span>  📋  View Download History</div>
                  <div><span className="text-[#58a6ff]">[4]</span>  ⚙  Settings</div>
                  <div><span className="text-[#58a6ff]">[5]</span>  ❌  Exit</div>
                </div>
              </div>
              <div className="text-[#8b949e]">▶ Enter <span className="text-[#3fb950]">1-5</span> or Q for Quick Download →{" "}
                <input className="bg-transparent outline-none text-white w-6 caret-green-400" value={inputLine} onChange={e => setInputLine(e.target.value)} onKeyDown={handleKey} autoFocus />
              </div>
            </>
          )}

          {screen === "quick" && (
            <>
              <div className="text-[#f0883e] font-bold mb-3">⚡ Quick Download</div>
              <div className="text-[#8b949e] mb-2">Paste a URL and AURY will download at your default quality (1080p).</div>
              <div className="text-[#8b949e]">▶ URL: <input className="bg-transparent outline-none text-[#58a6ff] w-80 caret-green-400" value={inputLine} onChange={e => setInputLine(e.target.value)} onKeyDown={handleKey} autoFocus placeholder="https://youtube.com/watch?v=..." /></div>
              <div className="text-[#8b949e] mt-4 text-xs">Press Enter to start · Leave blank to go back</div>
            </>
          )}

          {screen === "download" && (
            <div>
              <div className="text-[#58a6ff] font-bold mb-3">⬇ Start New Download</div>
              {dlStep >= 1 && (
                <div className="mb-2 text-[#8b949e]">
                  🔗 URL: <span className="text-[#58a6ff]">{dlUrl || <input className="bg-transparent outline-none text-[#58a6ff] w-72 caret-green-400" value={inputLine} onChange={e => setInputLine(e.target.value)} onKeyDown={handleKey} autoFocus placeholder="https://..." />}</span>
                </div>
              )}
              {dlStep >= 2 && (
                <div className="mb-3 text-[#8b949e]">
                  🎚 Quality: <span className="text-[#f0883e]">{dlQuality || <input className="bg-transparent outline-none text-[#f0883e] w-20 caret-green-400" value={inputLine} onChange={e => setInputLine(e.target.value)} onKeyDown={handleKey} autoFocus placeholder="1080p" />}</span>
                </div>
              )}
              {dlStep >= 3 && (
                <div className="mt-2">
                  <div className="text-[#3fb950] mb-2">🎬 Fetching metadata…</div>
                  <div className="text-[#e6edf3] mb-1 truncate">📄 <span className="text-white">Lofi Hip Hop Radio – Beats to Relax/Study to</span></div>
                  <div className="text-[#8b949e] text-xs mb-3">Duration: 2:07:33  ·  Platform: YouTube  ·  Quality: {dlQuality || "Best"}</div>
                  {downloading && (
                    <>
                      <div className="text-[#8b949e] text-xs mb-1">Downloading…  {Math.min(100, Math.floor(progress))}%</div>
                      <div className="font-mono text-[#3fb950] mb-1">[{bar(progress)}] {Math.min(100, Math.floor(progress))}%</div>
                      <div className="text-[#8b949e] text-xs">⚡ 14.2 MB/s  ·  ETA 0:38  ·  1.2 GB / 3.4 GB</div>
                    </>
                  )}
                  {done && (
                    <>
                      <div className="text-[#3fb950] font-bold mb-1">✅ Download complete!</div>
                      <div className="text-[#8b949e] text-xs mb-1">Saved to: ~/Downloads/AURY/video/lofi-hip-hop-radio.mp4</div>
                      <div className="text-[#8b949e] text-xs mb-3">Size: 1.24 GB  ·  Duration: 2:07:33  ·  Codec: H.264/AAC</div>
                      <div className="text-[#8b949e]">▶ Press Enter to return to menu → <input className="bg-transparent outline-none text-white w-4 caret-green-400" value={inputLine} onChange={e => setInputLine(e.target.value)} onKeyDown={handleKey} autoFocus /></div>
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {screen === "history" && (
            <div>
              <div className="text-[#e6edf3] font-bold mb-3">📋 Download History</div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-[#8b949e] border-b border-[#30363d]">
                      <th className="text-left py-1 pr-3">#</th>
                      <th className="text-left py-1 pr-4">Title</th>
                      <th className="text-left py-1 pr-3">Platform</th>
                      <th className="text-left py-1 pr-3">Quality</th>
                      <th className="text-left py-1 pr-3">Size</th>
                      <th className="text-left py-1 pr-3">Date</th>
                      <th className="text-left py-1">OK</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historyData.map(r => (
                      <tr key={r.id} className="border-b border-[#21262d] text-[#e6edf3]">
                        <td className="py-1 pr-3 text-[#8b949e]">{r.id}</td>
                        <td className="py-1 pr-4 max-w-[200px] truncate">{r.title}</td>
                        <td className="py-1 pr-3 text-[#58a6ff]">{r.platform}</td>
                        <td className="py-1 pr-3 text-[#f0883e]">{r.quality}</td>
                        <td className="py-1 pr-3">{r.size}</td>
                        <td className="py-1 pr-3 text-[#8b949e]">{r.date}</td>
                        <td className="py-1">{r.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 text-[#8b949e] text-xs">3 records  ·  Press B to go back → <input className="bg-transparent outline-none text-white w-4 caret-green-400" value={inputLine} onChange={e => setInputLine(e.target.value)} onKeyDown={handleKey} autoFocus /></div>
            </div>
          )}

          {screen === "settings" && (
            <div>
              <div className="text-[#e6edf3] font-bold mb-3">⚙ Settings</div>
              <div className="space-y-2 text-xs">
                {settingsData.map(([k, v], i) => (
                  <div key={i} className="flex gap-4">
                    <span className="text-[#8b949e] w-44">{k}</span>
                    <span className="text-[#3fb950]">{v}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 text-[#8b949e] text-xs">Press B to go back → <input className="bg-transparent outline-none text-white w-4 caret-green-400" value={inputLine} onChange={e => setInputLine(e.target.value)} onKeyDown={handleKey} autoFocus /></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
