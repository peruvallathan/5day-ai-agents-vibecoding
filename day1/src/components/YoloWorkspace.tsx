import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Scan,
  Maximize2,
  Cpu,
  Layers,
  Database,
  Eye,
  Crosshair,
  ShieldAlert
} from 'lucide-react';

interface StageProps {
  progress: number;
}

export const YoloWorkspace: React.FC<StageProps> = ({ progress }) => {
  // [0-20] Stage 1: Input Image
  // [20-40] Stage 2: Feature Extraction
  // [40-65] Stage 3: Detection Head (Anchors)
  // [65-85] Stage 4: Classification (Boxes appear)
  // [85-100] Stage 5: Final Output

  const stage = progress < 20 ? 1 : progress < 40 ? 2 : progress < 65 ? 3 : progress < 90 ? 4 : 5;

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center p-8 overflow-hidden">
      <div className="absolute top-8 left-8 flex items-center gap-2 text-emerald-500/60">
        <Scan size={16} />
        <span className="text-[10px] font-mono uppercase tracking-widest">Real-Time CV Pipeline</span>
      </div>

      <AnimatePresence mode="wait">
        {stage === 1 && (
          <motion.div 
            key="stage1"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.1 }}
            className="relative w-full max-w-3xl aspect-video rounded-xl border-2 border-obs-border bg-black/40 overflow-hidden"
          >
             {/* Abstract street scene representation */}
             <div className="absolute inset-0 bg-gradient-to-tr from-gray-900 to-black p-12 flex items-center justify-center">
                <div className="text-center space-y-4">
                    <Maximize2 className="mx-auto text-gray-700" size={48} />
                    <p className="text-xs font-mono text-gray-500 uppercase tracking-widest">Waiting for stream...</p>
                    <h2 className="text-2xl font-display text-white font-bold">L40S-NODE-04: TRAFFIC_CAM_01</h2>
                </div>
             </div>
             <motion.div 
               animate={{ y: ['0%', '100%'] }}
               transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
               className="absolute top-0 left-0 w-full h-1 bg-emerald-500/30 blur-sm shadow-[0_0_15px_rgba(16,185,129,0.5)]"
             />
          </motion.div>
        )}

        {stage === 2 && (
          <motion.div 
            key="stage2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-12 w-full"
          >
            <div className="flex items-center gap-4">
               <FeaturePyramid level={1} resolution="640x640" channels={3} />
               <Arrow />
               <FeaturePyramid level={2} resolution="320x320" channels={64} active={progress > 25} />
               <Arrow />
               <FeaturePyramid level={3} resolution="160x160" channels={128} active={progress > 30} />
               <Arrow />
               <FeaturePyramid level={4} resolution="80x80" channels={256} active={progress > 35} />
            </div>

            <div className="grid grid-cols-3 gap-12">
               <MetaStat label="Backbone" value="Darknet-v11" />
               <MetaStat label="Neck" value="PAN-FPN" />
               <MetaStat label="GFLOPs" value="12.4" />
            </div>
          </motion.div>
        )}

        {stage === 3 && (
          <motion.div 
            key="stage3"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="relative w-full max-w-3xl aspect-video rounded-xl border border-obs-border bg-black/60 overflow-hidden"
          >
             <div className="absolute inset-0 grid grid-cols-20 grid-rows-12">
                {[...Array(240)].map((_, i) => (
                  <motion.div 
                    key={i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: [0, 0.3, 0.1] }}
                    transition={{ delay: i * 0.002 }}
                    className="border-[0.5px] border-emerald-500/10 flex items-center justify-center"
                  >
                     {Math.random() > 0.95 && <div className="w-1 h-1 bg-emerald-500 shadow-[0_0_5px_emerald]" />}
                  </motion.div>
                ))}
             </div>
             
             <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center bg-black/80 px-8 py-4 rounded-lg border border-obs-border backdrop-blur">
                <Crosshair size={24} className="text-emerald-500 mx-auto mb-3" />
                <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Generating Proposals</p>
                <p className="text-xl font-display text-white font-bold">12,400 ANCHORS</p>
             </div>
          </motion.div>
        )}

        {(stage === 4 || stage === 5) && (
          <motion.div 
            key="stage4-5"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="relative w-full max-w-4xl grid grid-cols-3 gap-6"
          >
             <div className="col-span-2 relative aspect-video rounded-xl border-2 border-emerald-500/30 bg-black/40 overflow-hidden shadow-[0_0_30px_rgba(16,185,129,0.1)]">
                {/* Simulated Final Detection View */}
                <div className="absolute inset-0 bg-gray-900 border border-emerald-900/20" />
                
                {/* Detections */}
                <DetectionBox 
                   x="20%" y="30%" w="15%" h="40%" 
                   label="Person" conf={0.98} 
                   visible={progress > 68} 
                />
                <DetectionBox 
                   x="45%" y="45%" w="30%" h="25%" 
                   label="Car" conf={0.94} 
                   visible={progress > 75} 
                />
                <DetectionBox 
                   x="80%" y="15%" w="10%" h="15%" 
                   label="Traffic Light" conf={0.87} 
                   visible={progress > 82} 
                   color="border-amber-500 bg-amber-500/10"
                />

                <div className="absolute bottom-4 left-4 flex gap-4">
                    <div className="bg-black/60 backdrop-blur px-3 py-1.5 rounded border border-obs-border flex items-center gap-2">
                        <Eye size={12} className="text-emerald-500" />
                        <span className="text-[10px] font-mono text-white">4 OBJECTS</span>
                    </div>
                </div>
             </div>

             <div className="space-y-4">
                <h3 className="text-xs font-mono text-gray-500 uppercase tracking-widest px-1">Classification Logs</h3>
                <div className="flex flex-col gap-2">
                   <ClassLog label="Person" score={0.98} visible={progress > 68} />
                   <ClassLog label="Car" score={0.94} visible={progress > 75} />
                   <ClassLog label="Bicycle" score={0.91} visible={progress > 80} />
                   <ClassLog label="Traffic Light" score={0.87} visible={progress > 85} />
                </div>

                <div className="mt-8 p-4 rounded-lg bg-obs-surface border border-obs-border space-y-4">
                    <div className="flex justify-between items-center">
                        <span className="text-[10px] font-mono text-gray-500 uppercase">NMS Process</span>
                        <ShieldAlert size={12} className="text-emerald-500" />
                    </div>
                    <div className="h-2 w-full bg-black/40 rounded-full overflow-hidden">
                        <motion.div 
                          animate={{ width: stage === 5 ? '100%' : '60%' }}
                          className="h-full bg-emerald-500 shadow-[0_0_10px_emerald]" 
                        />
                    </div>
                    <div className="flex justify-between font-mono text-[10px] text-gray-400">
                      <span>IOU Threshold</span>
                      <span>0.45</span>
                    </div>
                </div>
             </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const FeaturePyramid = ({ level, resolution, channels, active = true }: { level: number; resolution: string; channels: number; active?: boolean }) => (
  <div className="flex flex-col items-center gap-3">
    <motion.div 
      animate={{ 
        scale: active ? 1 : 0.8,
        opacity: active ? 1 : 0.2
      }}
      className={`rounded bg-emerald-500/20 border ${active ? 'border-emerald-500' : 'border-emerald-900'} p-3 flex flex-col items-center justify-center`}
      style={{ width: 80 - level * 10, height: 80 - level * 10 }}
    >
       <Layers size={20 - level * 2} className={active ? 'text-emerald-400' : 'text-emerald-900'} />
    </motion.div>
    <div className="text-center space-y-1">
        <p className="text-[9px] font-mono text-gray-500 uppercase">P{level}</p>
        <p className="text-[10px] font-mono text-white">{resolution}</p>
        <p className="text-[10px] font-mono text-emerald-500/60">C={channels}</p>
    </div>
  </div>
);

const Arrow = () => <div className="w-4 h-[1px] bg-obs-border mt-[-20px]" />;

const MetaStat = ({ label, value }: { label: string; value: string }) => (
  <div className="text-center space-y-1">
    <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">{label}</p>
    <p className="text-lg font-display text-white font-bold">{value}</p>
  </div>
);

const DetectionBox = ({ x, y, w, h, label, conf, visible, color = "border-emerald-500 bg-emerald-500/10" }: any) => {
  if (!visible) return null;
  return (
    <motion.div 
      initial={{ opacity: 0, scale: 1.1 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`absolute border-2 ${color} flex flex-col items-start`}
      style={{ left: x, top: y, width: w, height: h }}
    >
      <div className="bg-emerald-500 text-black text-[9px] font-mono font-bold px-1 py-0.5">
        {label} {(conf * 100).toFixed(0)}%
      </div>
      <div className="absolute -top-1 -left-1 w-2 h-2 bg-white" />
      <div className="absolute -bottom-1 -right-1 w-2 h-2 bg-white" />
    </motion.div>
  );
};

const ClassLog = ({ label, score, visible }: { label: string; score: number; visible: boolean }) => (
  <div className={`flex items-center justify-between p-3 rounded border border-obs-border transition-all duration-500 ${visible ? 'bg-white/[0.03] opacity-100' : 'opacity-20'}`}>
     <span className="text-[11px] text-gray-300">{label}</span>
     <div className="flex items-center gap-3">
        <div className="w-24 h-1 bg-black rounded-full overflow-hidden">
            <motion.div 
              initial={{ width: 0 }}
              animate={{ width: visible ? `${score * 100}%` : 0 }}
              className="h-full bg-emerald-500"
            />
        </div>
        <span className="text-[10px] font-mono text-emerald-500">{(score * 100).toFixed(0)}%</span>
     </div>
  </div>
);
