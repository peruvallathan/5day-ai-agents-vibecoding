/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Network, 
  Eye, 
  Play, 
  RotateCcw,
  Activity
} from 'lucide-react';
import { SidebarLeft } from './components/SidebarLeft';
import { SidebarRight } from './components/SidebarRight';
import { TransformerWorkspace } from './components/TransformerWorkspace';
import { YoloWorkspace } from './components/YoloWorkspace';
import { ModelMode, TelemetryMetrics, TransformerExtras, YoloExtras } from './types';
import { TRANSFORMER_METADATA, YOLO_METADATA, INITIAL_TELEMETRY } from './data';

export default function App() {
  const [activeMode, setActiveMode] = useState<ModelMode>('TRANSFORMER');
  const [isSimulating, setIsSimulating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [metrics, setMetrics] = useState<TelemetryMetrics>(INITIAL_TELEMETRY);
  
  const simulationInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  // Mode switching resets
  useEffect(() => {
    stopSimulation();
    setProgress(0);
    setMetrics(INITIAL_TELEMETRY);
  }, [activeMode]);

  const startSimulation = () => {
    if (isSimulating) return;
    setIsSimulating(true);
    setProgress(0);
    
    simulationInterval.current = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(simulationInterval.current!);
          setIsSimulating(false);
          return 100;
        }
        return prev + 1;
      });

      // Randomized metrics jitter for realism
      setMetrics(prev => ({
        ...prev,
        gpuUtil: Math.min(98, prev.gpuUtil + (Math.random() * 5 - 2)),
        latency: Math.max(8, prev.latency + (Math.random() * 2 - 1)),
        layerProgress: progress
      }));
    }, 50); // 5 seconds approximately (100 steps * 50ms)
  };

  const stopSimulation = () => {
    if (simulationInterval.current) {
        clearInterval(simulationInterval.current);
    }
    setIsSimulating(false);
    setProgress(0);
  };

  const transformerExtras: TransformerExtras = {
    entropy: 1.24 + (progress / 100) * 0.5,
    tokensProcessed: Math.floor((progress / 100) * 2048),
    activeLayer: Math.floor((progress / 100) * 96)
  };

  const yoloExtras: YoloExtras = {
    detections: Math.floor((progress / 100) * 12),
    anchorDensity: 12.4,
    nmsProgress: progress,
    avgConfidence: 0.85 + (progress / 100) * 0.1
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[#050506] overflow-hidden text-slate-300 font-sans select-none">
      {/* Top Header */}
      <header className="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-[#050506]/80 backdrop-blur-md z-50">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" />
          <span className="font-semibold tracking-wider text-white text-sm uppercase">
            Aegis Observability Console <span className="text-blue-500 opacity-80 ml-2">v2.4.0</span>
          </span>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex gap-6 text-[10px] uppercase tracking-[0.2em] font-bold">
            <span className="text-blue-400">System: Healthy</span>
            <span className="text-slate-500">Cluster: us-east-1-ais</span>
          </div>
          <div className="w-8 h-8 rounded-full border border-white/10 bg-gradient-to-br from-slate-700 to-slate-900 shadow-inner" />
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <SidebarLeft 
          metadata={activeMode === 'TRANSFORMER' ? TRANSFORMER_METADATA : YOLO_METADATA} 
          mode={activeMode}
        />

        <main className="flex-1 flex flex-col relative bg-[#020203]">
          {/* Ambient Background Glow */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-600/10 blur-[120px] rounded-full pointer-events-none" />

          {/* Workspace */}
          <div className="flex-1 relative overflow-hidden flex flex-col">
             <div className="p-8 pb-0">
               <h3 className="text-sm font-medium text-white mb-1">
                 {activeMode === 'TRANSFORMER' ? 'Multi-Head Attention Map' : 'Real-Time Object Detection Pipeline'} 
                 <span className="text-slate-500 font-normal ml-3">— {activeMode === 'TRANSFORMER' ? 'Layer 24' : 'Backbone v11'}</span>
               </h3>
               <p className="text-[11px] text-slate-500">
                 {activeMode === 'TRANSFORMER' ? 'Real-time weight activation across query-key subspaces.' : 'Neural feature extraction and classification stream.'}
               </p>
             </div>

             <AnimatePresence mode="wait">
               <motion.div
                 key={activeMode}
                 initial={{ opacity: 0, scale: 0.98 }}
                 animate={{ opacity: 1, scale: 1 }}
                 exit={{ opacity: 0, scale: 1.02 }}
                 transition={{ duration: 0.4 }}
                 className="flex-1 m-8 border border-white/5 rounded-2xl bg-black/40 backdrop-blur-sm relative overflow-hidden"
               >
                 {activeMode === 'TRANSFORMER' ? (
                   <TransformerWorkspace progress={progress} />
                 ) : (
                   <YoloWorkspace progress={progress} />
                 )}
               </motion.div>
             </AnimatePresence>
          </div>

          {/* Workspace Controls */}
          <div className="h-28 px-8 flex flex-col justify-center gap-4 border-t border-white/5 bg-[#050506]/40 backdrop-blur-md">
            <div className="flex gap-4">
              <ModeButton 
                  active={activeMode === 'TRANSFORMER'} 
                  onClick={() => setActiveMode('TRANSFORMER')}
                  icon={<Network size={18} />}
                  label="Visualize Transformer Attention"
              />
              <ModeButton 
                  active={activeMode === 'YOLO'} 
                  onClick={() => setActiveMode('YOLO')}
                  icon={<Eye size={18} />}
                  label="Simulate YOLO Inference"
              />
              <div className="ml-auto flex gap-3 h-12">
                 <button 
                    onClick={startSimulation}
                    disabled={isSimulating}
                    className={`flex items-center gap-3 px-8 rounded-xl font-display font-bold uppercase tracking-wider text-xs transition-all ${
                        isSimulating 
                        ? 'bg-white/5 text-slate-500 cursor-not-allowed border border-white/5' 
                        : 'bg-blue-600 text-white hover:bg-blue-500 active:scale-95 shadow-[0_0_20px_rgba(59,130,246,0.3)]'
                    }`}
                 >
                    <Play size={14} fill={!isSimulating ? 'currentColor' : 'none'} />
                    <span>Run Session</span>
                 </button>
                 <button 
                    onClick={stopSimulation}
                    className="w-12 h-12 rounded-xl border border-white/10 bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-all flex items-center justify-center active:scale-95"
                 >
                    <RotateCcw size={16} />
                 </button>
              </div>
            </div>
          </div>
        </main>

        <SidebarRight 
          metrics={metrics} 
          mode={activeMode} 
          extras={activeMode === 'TRANSFORMER' ? transformerExtras : yoloExtras} 
        />
      </div>

      {/* Footer Status Bar */}
      <footer className="h-8 border-t border-white/5 px-4 flex items-center justify-between text-[10px] bg-[#070709] shrink-0">
        <div className="flex gap-6">
          <span className="text-slate-500 font-mono">GPU_TEMP: <span className="text-emerald-400">42.4°C</span></span>
          <span className="text-slate-500 font-mono">UPTIME: <span className="text-slate-300">112:14:02:18</span></span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
          <span className="text-slate-500 tracking-tight">Streaming Telemetry: TLS 1.3 Encryption Active</span>
        </div>
      </footer>
    </div>
  );
}

const ModeButton = ({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) => (
  <button 
    onClick={onClick}
    className={`h-12 flex-1 max-w-[280px] flex items-center justify-center gap-3 rounded-xl border transition-all duration-300 text-[10px] uppercase font-bold tracking-widest ${
        active 
        ? 'bg-blue-600/20 border-blue-500/50 text-white shadow-[0_0_20px_rgba(59,130,246,0.1)] ring-2 ring-blue-500/20' 
        : 'bg-white/5 border-white/10 text-slate-500 hover:bg-white/10 hover:text-slate-300'
    }`}
  >
    <div className={`${active ? 'text-blue-400' : 'text-slate-600'}`}>{icon}</div>
    <span>{label}</span>
  </button>
);
