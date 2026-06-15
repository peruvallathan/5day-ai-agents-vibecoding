import React from 'react';
import { motion } from 'motion/react';
import { 
  Database, 
  Cpu, 
  Layers, 
  Zap, 
  Activity, 
  Maximize, 
  Box, 
  BarChart3, 
  Server, 
  Terminal,
  Info
} from 'lucide-react';
import { ModelMetadata } from '../types';

interface SidebarLeftProps {
  metadata: ModelMetadata;
  mode: 'TRANSFORMER' | 'YOLO';
}

export const SidebarLeft: React.FC<SidebarLeftProps> = ({ metadata, mode }) => {
  return (
    <aside className="w-64 h-full flex flex-col gap-6 p-5 border-r border-obs-border bg-obs-surface overflow-y-auto custom-scrollbar">
      <div className="flex items-center gap-2 px-1">
        <div className="w-2 h-2 rounded-full bg-brand-blue animate-pulse" />
        <span className="text-[10px] font-bold tracking-[0.2em] text-slate-500 uppercase">Model Metadata</span>
      </div>

      <div className="flex flex-col gap-3 p-3 rounded-lg bg-white/5 border border-white/5">
        <label className="text-[9px] uppercase text-slate-500 block">Active Model</label>
        <h2 className="text-sm font-mono text-white tracking-tight uppercase">{metadata.name}</h2>
      </div>

      <div className="flex flex-col gap-3">
        <MetaItem label="Architecture" value={metadata.architecture} />
        <MetaItem label="Parameters" value={metadata.parameters} />
        <MetaItem label="Device" value={metadata.device} isBlue />
        <MetaItem label="Precision" value={metadata.precision} />
        <MetaItem label="Input Res" value={metadata.resolution} />
        <MetaItem label="Batch Size" value={metadata.batchSize} />
        <MetaItem label="Memory" value={metadata.memory} />
        <MetaItem label="Status" value={metadata.status} isStatus />
      </div>

      <div className="mt-auto p-4 rounded-lg border border-brand-blue/20 bg-brand-blue/5 flex flex-col gap-1">
        <span className="text-[9px] text-brand-blue uppercase tracking-widest font-bold">Throughput</span>
        <div className="flex items-end gap-2">
            <span className="text-2xl font-light text-white">{metadata.throughput.split(' ')[0]}</span>
            <span className="text-[10px] text-brand-blue/60 mb-1.5 uppercase font-mono">{metadata.throughput.split(' ')[1]}</span>
        </div>
      </div>
    </aside>
  );
};

const MetaItem = ({ label, value, isBlue, isStatus }: { label: string; value: string; isBlue?: boolean; isStatus?: boolean }) => (
  <div className="flex justify-between items-center border-b border-white/5 pb-2.5 group">
    <span className="text-[11px] text-slate-400 group-hover:text-slate-300 transition-colors uppercase tracking-tight">{label}</span>
    <span className={`text-[11px] font-medium truncate max-w-[120px] transition-all ${
        isBlue ? 'text-brand-blue font-mono' : 
        isStatus ? 'text-emerald-400 px-2 py-0.5 rounded bg-emerald-400/10 text-[9px] uppercase' :
        'text-white'
    }`}>
      {value}
    </span>
  </div>
);
