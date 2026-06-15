import React from 'react';
import { motion } from 'motion/react';
import { 
  TrendingUp, 
  Cpu, 
  Clock, 
  BarChart, 
  ShieldCheck,
  Zap,
  Layers,
  Search
} from 'lucide-react';
import { TelemetryMetrics, TransformerExtras, YoloExtras } from '../types';

interface SidebarRightProps {
  metrics: TelemetryMetrics;
  mode: 'TRANSFORMER' | 'YOLO';
  extras: TransformerExtras | YoloExtras;
}

export const SidebarRight: React.FC<SidebarRightProps> = ({ metrics, mode, extras }) => {
  return (
    <aside className="w-72 h-full flex flex-col gap-8 p-5 border-l border-obs-border bg-obs-surface overflow-y-auto custom-scrollbar">
      <div className="flex items-center gap-2 px-1">
        <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
        <span className="text-[10px] font-bold tracking-[0.2em] text-slate-500 uppercase">Live Telemetry</span>
      </div>

      <div className="flex flex-col gap-6">
        <MetricProgress label="GPU Utilization" value={metrics.gpuUtil} color="bg-blue-500" shadow="shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
        <MetricProgress label="VRAM Usage" value={metrics.vramUsage} color="bg-brand-purple" suffix=" / 80 GB" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <MetricCard label="Latency" value={`${metrics.latency}ms`} />
        <MetricCard label="FPS" value={metrics.fps.toString()} />
        <MetricCard label={mode === 'TRANSFORMER' ? 'Entropy' : 'Detections'} value={mode === 'TRANSFORMER' ? (extras as TransformerExtras).entropy.toFixed(2) : (extras as YoloExtras).detections.toString()} />
        <MetricCard label="Q-Depth" value={`0${metrics.queueDepth}`} />
      </div>

      <div className="space-y-4">
          <div className="text-[9px] text-slate-500 uppercase tracking-widest font-bold">Inference Activity</div>
          <div className="h-20 w-full flex items-end gap-[2px]">
            {[...Array(15)].map((_, i) => (
                <motion.div 
                   key={i}
                   initial={{ height: '20%' }}
                   animate={{ height: [`${Math.random() * 60 + 20}%`, `${Math.random() * 60 + 20}%`] }}
                   transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.1 }}
                   className={`w-full rounded-t-sm ${i === 7 ? 'bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.3)]' : 'bg-blue-500/20'}`} 
                />
            ))}
          </div>
      </div>

      <div className="mt-auto pt-6 border-t border-white/5">
          <div className="text-[9px] text-slate-500 uppercase font-bold mb-3 tracking-widest">Event Log</div>
          <div className="text-[10px] font-mono space-y-1.5 h-24 overflow-hidden mask-fade-bottom">
            <div className="text-emerald-400 opacity-80 uppercase">[04:21:02] LAYER_24_COMMIT_SUCCESS</div>
            <div className="text-slate-500 uppercase">[04:21:03] CACHE_KV_REALLOCATE</div>
            <div className="text-slate-500 uppercase">[04:21:03] ATTN_HEAD_32_FLUSH</div>
            <div className="text-brand-blue uppercase">[04:21:04] TOKEN_GEN_ID_8829</div>
          </div>
      </div>
    </aside>
  );
};

const MetricProgress = ({ label, value, color, shadow, suffix }: { label: string; value: number; color: string; shadow?: string; suffix?: string }) => (
  <div className="flex flex-col gap-2">
    <div className="flex items-center justify-between">
      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">{label}</span>
      <span className={`text-[10px] font-mono ${color.replace('bg-', 'text-')}`}>{value}{suffix || '%'}</span>
    </div>
    <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
      <motion.div 
        animate={{ width: `${value}%` }}
        className={`h-full ${color} ${shadow || ''}`}
      />
    </div>
  </div>
);

const MetricCard = ({ label, value }: { label: string; value: string }) => (
  <div className="p-3 rounded-lg bg-white/5 border border-white/5 flex flex-col gap-1 transition-all hover:bg-white/[0.08]">
    <div className="text-[9px] text-slate-500 uppercase font-bold tracking-tighter">{label}</div>
    <div className="text-sm font-mono text-white">{value}</div>
  </div>
);
