import React, { useState, useEffect } from 'react';
import { SystemPulse } from './components/SystemPulse';
import { mockStats, mockMemory, mockTranscript } from './data/mockData';
import { Database, MessageSquare, Terminal, Activity } from 'lucide-react';

const App: React.FC = () => {
  const [status, setStatus] = useState("DISCONNECTED");
  const [stats, setStats] = useState(mockStats);
  const [transcript, setTranscript] = useState(mockTranscript);
  const [emotion, setEmotion] = useState("neutral"); // neutral, productive, stressed, alert
  const [socket, setSocket] = useState<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket('ws://localhost:8000/ws');
      ws.onopen = () => setStatus("CONNECTED");
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'status') setStatus(msg.data);
        if (msg.type === 'stats') setStats(msg.data);
        if (msg.type === 'emotion') setEmotion(msg.data);
        if (msg.type === 'transcript') setTranscript(prev => [msg.data, ...prev].slice(0, 10));
      };
      ws.onclose = () => {
        setStatus("RECONNECTING...");
        setTimeout(connect, 3000);
      };
      setSocket(ws);
    };
    connect();
    return () => socket?.close();
  }, []);

  const auraMap: Record<string, string> = {
    neutral: 'bg-[#050505]',
    productive: 'bg-gradient-to-br from-[#050505] via-[#051a14] to-[#052a1a]', // Matrix Green hint
    stressed: 'bg-gradient-to-br from-[#050505] via-[#050e1a] to-[#051a2a]', // Calm Blue hint
    alert: 'bg-gradient-to-br from-[#050505] via-[#1a0505] to-[#2a0505]', // Alert Red hint
  };

  return (
    <div className={`min-h-screen ${auraMap[emotion] || auraMap.neutral} text-white p-8 font-inter selection:bg-cyan-500/30 transition-colors duration-1000`}>
      {/* Header */}
      <div className="flex justify-between items-center mb-12">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-cyan-500 rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.5)]">
            <Activity size={28} className="text-black" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tighter uppercase font-mono italic">Rocky Omega</h1>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${status === 'CONNECTED' ? 'bg-green-500' : 'bg-red-500'} animate-pulse`} />
              <span className="text-[10px] text-white/40 uppercase tracking-widest">{status}</span>
            </div>
          </div>
        </div>
        <div className="px-4 py-2 bg-white/5 backdrop-blur-md rounded-lg border border-white/10 text-xs font-mono text-white/60">
          SECURE PROTOCOL v1.4.0
        </div>
      </div>

      <main className="flex flex-col gap-12 items-center">
        {/* Top Gauges */}
        <SystemPulse stats={stats} />

        {/* Middle Content: Memory & Logs */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 w-full max-w-7xl">
          {/* Active Memory */}
          <section className="bg-white/5 backdrop-blur-lg rounded-3xl border border-white/10 p-8 shadow-xl">
            <div className="flex items-center gap-3 mb-6">
              <Database size={20} className="text-purple-400" />
              <h2 className="text-sm font-bold uppercase tracking-widest text-white/60">Active Memory Bank</h2>
            </div>
            <div className="space-y-4">
              {mockMemory.map((item: any) => (
                <div key={item.id} className="flex justify-between items-center p-4 bg-white/5 rounded-2xl border border-white/5 hover:border-purple-500/30 transition-all cursor-default group">
                  <span className="text-sm text-white/80">{item.text}</span>
                  <span className="text-[10px] bg-purple-500/20 text-purple-300 px-2 py-1 rounded-md uppercase font-bold">{item.category}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Transcript Stream */}
          <section className="bg-white/5 backdrop-blur-lg rounded-3xl border border-white/10 p-8 shadow-xl">
            <div className="flex items-center gap-3 mb-6">
              <MessageSquare size={20} className="text-green-400" />
              <h2 className="text-sm font-bold uppercase tracking-widest text-white/60">Transcript Stream</h2>
            </div>
            <div className="space-y-6 max-h-[400px] overflow-y-auto pr-4 scrollbar-hide">
              {transcript.map((t: any, i: number) => (
                <div key={i} className="space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-500">
                  <div className="flex gap-2">
                    <span className="text-[10px] font-mono text-white/20 uppercase mt-1">USER</span>
                    <p className="text-sm text-white/60 italic">{t.user}</p>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-[10px] font-mono text-cyan-400 uppercase mt-1">AI</span>
                    <p className="text-sm text-cyan-500 font-medium leading-relaxed">{t.ai}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Console / Command Bridge */}
        <div className="w-full max-w-7xl bg-[#0a0a0c] p-4 rounded-2xl border border-white/10 font-mono text-[11px] text-green-500/70 flex gap-4">
          <Terminal size={14} />
          <span>[SYSTEM] Monitoring local filesystem... Sentinel background thread active...</span>
        </div>
      </main>
    </div>
  );
};

export default App;
