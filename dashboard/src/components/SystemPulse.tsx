import React from 'react';
import { Cpu, MemoryStick, Brain } from 'lucide-react';

interface GaugeProps {
  label: string;
  value: number;
  max: number;
  unit: string;
  icon: React.ReactNode;
  color: string;
}

const Gauge: React.FC<GaugeProps> = ({ label, value, max, unit, icon, color }) => {
  const percentage = (value / max) * 100;
  const radius = 80;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-6 bg-white/5 backdrop-blur-xl rounded-3xl border border-white/10 shadow-2xl transition-all hover:scale-105 group">
      <div className="relative w-40 h-40 flex items-center justify-center">
        {/* Track */}
        <svg className="absolute w-full h-full -rotate-90">
          <circle
            cx="80"
            cy="80"
            r={radius}
            stroke="currentColor"
            strokeWidth="8"
            fill="transparent"
            className="text-white/5"
          />
          {/* Active Progress */}
          <circle
            cx="80"
            cy="80"
            r={radius}
            stroke={color}
            strokeWidth="8"
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
            style={{ filter: `drop-shadow(0 0 8px ${color})` }}
          />
        </svg>
        <div className="z-10 flex flex-col items-center">
          <div className="p-3 bg-white/10 rounded-full mb-1 text-cyan-400 group-hover:animate-pulse">
            {icon}
          </div>
          <span className="text-2xl font-bold text-white font-mono">{value}{unit}</span>
          <span className="text-xs uppercase tracking-widest text-white/40">{label}</span>
        </div>
      </div>
    </div>
  );
};

export const SystemPulse: React.FC<{ stats: any }> = ({ stats }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full max-w-5xl">
      <Gauge 
        label="CPU Load" 
        value={stats.cpu || 0} 
        max={100} 
        unit="%" 
        icon={<Cpu size={24} />} 
        color="#00f2ff" 
      />
      <Gauge 
        label="Memory" 
        value={parseFloat(stats.memory) || 0} 
        max={32} 
        unit="GB" 
        icon={<MemoryStick size={24} />} 
        color="#bf00ff" 
      />
      <Gauge 
        label="LLM Brain" 
        value={stats.llm === 'Idle' ? 10 : 90} 
        max={100} 
        unit="%" 
        icon={<Brain size={24} />} 
        color="#00ffa3" 
      />
    </div>
  );
};
