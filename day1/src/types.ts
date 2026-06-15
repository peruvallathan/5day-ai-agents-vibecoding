export type ModelMode = 'TRANSFORMER' | 'YOLO';

export interface ModelMetadata {
  name: string;
  architecture: string;
  parameters: string;
  device: string;
  precision: string;
  resolution: string;
  batchSize: string;
  throughput: string;
  flops: string;
  memory: string;
  status: string;
  environment: string;
  framework: string;
}

export interface TelemetryMetrics {
  gpuUtil: number;
  cpuUtil: number;
  vramUsage: number;
  latency: number;
  fps: number;
  throughput: number;
  layerProgress: number;
  confidence: number;
  queueDepth: number;
}

export interface TransformerExtras {
  entropy: number;
  tokensProcessed: number;
  activeLayer: number;
}

export interface YoloExtras {
  detections: number;
  anchorDensity: number;
  nmsProgress: number;
  avgConfidence: number;
}
