import { ModelMetadata, TelemetryMetrics } from './types';

export const TRANSFORMER_METADATA: ModelMetadata = {
  name: 'GPT-NeoX-7B',
  architecture: 'Decoder-only Transformer',
  parameters: '7.4B',
  device: 'NVIDIA H100 (80GB)',
  precision: 'BFloat16',
  resolution: '2048 Context',
  batchSize: '128',
  throughput: '14,200 tps',
  flops: '124 TFLOPS',
  memory: '14.8 GB',
  status: 'Ready / Inference',
  environment: 'Kubernetes / vLLM',
  framework: 'PyTorch 2.4.0'
};

export const YOLO_METADATA: ModelMetadata = {
  name: 'YOLOv11-Extreme',
  architecture: 'CSP-Darknet-v11',
  parameters: '58.4M',
  device: 'NVIDIA L40S',
  precision: 'FP16',
  resolution: '640x640',
  batchSize: '1',
  throughput: '185 FPS',
  flops: '12.4 GFLOPS',
  memory: '1.2 GB',
  status: 'Streaming',
  environment: 'Edge Deployment',
  framework: 'Ultralytics 8.3'
};

export const INITIAL_TELEMETRY: TelemetryMetrics = {
  gpuUtil: 45,
  cpuUtil: 22,
  vramUsage: 35,
  latency: 12.4,
  fps: 144,
  throughput: 88,
  layerProgress: 0,
  confidence: 0.92,
  queueDepth: 4
};
