import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Square,
  Cpu,
  Layers,
  ArrowRight,
  Sparkles,
  Search,
  CheckCircle2,
  Share2
} from 'lucide-react';

interface StageProps {
  progress: number;
}

const tokens = ["The", "cat", "is", "sitting", "on", "the", "mat."];

export const TransformerWorkspace: React.FC<StageProps> = ({ progress }) => {
  // progress 0-100 determines which stage we show
  // [0-20] Stage 1: Input
  // [20-40] Stage 2: Embeddings
  // [40-80] Stage 3: Stack
  // [80-100] Stage 4: Output

  const stage = progress < 20 ? 1 : progress < 40 ? 2 : progress < 85 ? 3 : 4;

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center p-8 overflow-hidden">
      <div className="absolute top-8 left-8 flex items-center gap-2 text-brand-blue/60">
        <Sparkles size={16} />
        <span className="text-[10px] font-mono uppercase tracking-widest">Neural Computation Engine</span>
      </div>

      <AnimatePresence mode="wait">
        {stage === 1 && (
          <motion.div 
            key="stage1"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex flex-col items-center gap-8 w-full max-w-2xl"
          >
            <div className="text-center space-y-2">
              <h3 className="text-xs font-mono text-gray-500 uppercase tracking-widest">Input Stream</h3>
              <p className="text-2xl font-display text-white font-medium">&quot;The cat is sitting on the mat.&quot;</p>
            </div>
            
            <div className="flex flex-wrap justify-center gap-3">
              {tokens.map((token, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.05 }}
                  className="px-4 py-2 rounded border border-white/10 bg-white/5 text-brand-blue font-mono text-sm"
                >
                  [{token}]
                </motion.div>
              ))}
            </div>
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
            <div className="grid grid-cols-7 gap-8">
              {tokens.map((_, i) => (
                <div key={i} className="flex flex-col items-center gap-4">
                  <div className="w-px h-12 bg-gradient-to-b from-brand-blue/50 to-transparent" />
                  <div className="relative">
                    <motion.div 
                      animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
                      transition={{ repeat: Infinity, duration: 2, delay: i * 0.2 }}
                      className="absolute inset-0 bg-brand-blue blur-lg"
                    />
                    <div className="relative w-12 h-12 rounded-lg border border-brand-blue/50 bg-brand-blue/20 flex items-center justify-center">
                        <Square className="text-brand-blue" size={20} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            <div className="flex gap-12 text-center">
              <MetadataStat label="Tokens" value="7" />
              <MetadataStat label="Seq Len" value="2048" />
              <MetadataStat label="d_model" value="4096" />
            </div>
          </motion.div>
        )}

        {stage === 3 && (
          <motion.div 
            key="stage3"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="w-full max-w-4xl h-[600px] relative flex items-center justify-center"
          >
            {/* Visualizing layers as stacked blocks */}
            <div className="flex items-center gap-1">
               {[...Array(8)].map((_, i) => (
                 <LayerBlock 
                    key={i} 
                    index={i} 
                    active={Math.floor((progress - 40) / 5) === i}
                 />
               ))}
            </div>

            {/* Simulated attention lines */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-40">
                <AttentionLines count={20} />
            </svg>

            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-8 whitespace-nowrap bg-black/40 backdrop-blur border border-obs-border px-6 py-3 rounded-full">
               <LayerLabel label="Self-Attention" value="Active" />
               <LayerLabel label="Heads" value="32" />
               <LayerLabel label="Score" value="0.984" />
            </div>
          </motion.div>
        )}

        {stage === 4 && (
          <motion.div 
            key="stage4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center gap-10 w-full max-w-xl"
          >
            <div className="w-16 h-16 rounded-full bg-brand-blue/20 border border-brand-blue/40 flex items-center justify-center relative">
                <CheckCircle2 size={32} className="text-brand-blue" />
                <motion.div 
                  animate={{ scale: [1, 1.5], opacity: [1, 0] }}
                  transition={{ duration: 1, repeat: Infinity }}
                  className="absolute inset-0 rounded-full border border-brand-blue"
                />
            </div>

            <div className="w-full p-6 glass-panel space-y-6">
                <div className="flex items-center justify-between border-b border-obs-border pb-4">
                    <span className="text-xs font-mono text-gray-500 uppercase tracking-widest">Inference Result</span>
                    <span className="text-xs font-display text-brand-blue font-bold tracking-tight">POSITIVE SENTIMENT</span>
                </div>

                <div className="space-y-4">
                    <ProbabilityBar label="Neutral" value={8} />
                    <ProbabilityBar label="Positive" value={88} color="bg-brand-blue" />
                    <ProbabilityBar label="Negative" value={4} />
                </div>
            </div>

            <p className="text-gray-400 font-display italic text-center text-lg">&quot;The cat appears relaxed and comfortable.&quot;</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const MetadataStat = ({ label, value }: { label: string; value: string }) => (
  <div className="space-y-1">
    <p className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">{label}</p>
    <p className="text-xl font-display text-white font-bold">{value}</p>
  </div>
);

const LayerBlock = ({ index, active }: { index: number; active: boolean }) => (
  <div className="flex flex-col items-center gap-2 relative">
    <motion.div 
      initial={false}
      animate={{ 
        height: active ? 160 : 120,
        width: active ? 60 : 40,
        backgroundColor: active ? 'rgba(59, 130, 246, 0.4)' : 'rgba(255, 255, 255, 0.03)',
        borderColor: active ? 'rgba(59, 130, 246, 0.6)' : 'rgba(255, 255, 255, 0.1)'
      }}
      className="rounded-md border flex flex-col items-center justify-center gap-1 transition-all"
    >
      <span className={`text-[10px] font-mono ${active ? 'text-white' : 'text-gray-600'}`}>L{index + 1}</span>
      {active && <Cpu size={14} className="text-brand-blue animate-pulse" />}
    </motion.div>
    {index < 7 && <ArrowRight size={14} className="text-gray-700 mx-2" />}
  </div>
);

const AttentionLines = ({ count }: { count: number }) => (
  <>
    {[...Array(count)].map((_, i) => {
      const x1 = 100 + Math.random() * 800;
      const y1 = 100 + Math.random() * 300;
      const x2 = 100 + Math.random() * 800;
      const y2 = 100 + Math.random() * 300;
      
      return (
        <motion.line
          key={i}
          x1={x1} y1={y1} x2={x2} y2={y2}
          stroke="url(#grad1)"
          strokeWidth="0.5"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: [0, 0.4, 0] }}
          transition={{ 
            duration: 2 + Math.random() * 2, 
            repeat: Infinity, 
            delay: Math.random() * 5 
          }}
        />
      );
    })}
    <defs>
      <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stopColor="#3b82f6" />
        <stop offset="100%" stopColor="#8b5cf6" />
      </linearGradient>
    </defs>
  </>
);

const LayerLabel = ({ label, value }: { label: string; value: string }) => (
  <div className="flex gap-2 items-baseline">
    <span className="text-[10px] font-mono text-gray-500 uppercase">{label}:</span>
    <span className="text-xs font-mono text-white">{value}</span>
  </div>
);

const ProbabilityBar = ({ label, value, color = "bg-white/10" }: { label: string; value: number; color?: string }) => (
  <div className="space-y-1.5">
    <div className="flex justify-between text-[10px] font-mono uppercase text-gray-400">
      <span>{label}</span>
      <span>{value}%</span>
    </div>
    <div className="h-1.5 w-full bg-obs-border rounded-full overflow-hidden">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          className={`h-full ${color}`}
        />
    </div>
  </div>
);
