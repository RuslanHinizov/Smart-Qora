export type Role = "admin" | "viewer";
export type Direction = "IN" | "OUT";
export type InsideDirection = "UP" | "DOWN" | "LEFT" | "RIGHT";
export type CameraStatus = "ONLINE" | "OFFLINE" | "RECONNECTING";
export type AiStatus = "ACTIVE" | "IDLE";
export type WorkerState = "starting" | "running" | "restarting" | "stopped" | "failed";

export type LoginResponse = { access_token: string; token_type: string; role: Role };
export type Me = { id: number; username: string; role: Role; is_active: boolean };

export type SystemStatus = {
  camera: CameraStatus | string;
  ai: AiStatus | string;
  worker: WorkerState | string;
  restarts: number;
  last_error: string | null;
  languages: string[];
};

export type WorkerInfo = {
  state: WorkerState | string;
  restarts: number;
  last_error: string | null;
  camera: CameraStatus | string;
};

export type Totals = { total_in: number; total_out: number; current: number };

export type EventRow = {
  id: number;
  camera_id: number;
  animal_type: string;
  tracking_id: number;
  crossing_sequence: number;
  direction: Direction;
  confidence: number;
  timestamp: string;
};

export type Camera = {
  id: number;
  name: string;
  source: string;
  location: string;
  is_active: boolean;
  line_p1_x: number | null;
  line_p1_y: number | null;
  line_p2_x: number | null;
  line_p2_y: number | null;
  inside_direction: InsideDirection | null;
  confidence: number | null;
  iou: number | null;
  frame_skip: number;
  stream_fps: number;
  created_at: string;
};

export type CameraInput = Omit<Camera, "id" | "created_at">;

export type AppSettings = {
  default_language: string;
  telegram_configured: boolean;
  telegram_aggregation_seconds: number;
  default_confidence: number | null;
  default_iou: number | null;
  default_frame_skip: number | null;
  stream_fps: number | null;
};

export type SettingsInput = Partial<{
  default_language: string;
  telegram_bot_token: string;
  telegram_chat_id: string;
  telegram_aggregation_seconds: number;
  default_confidence: number | null;
  default_iou: number | null;
  default_frame_skip: number | null;
  stream_fps: number | null;
}>;

export type HistoryRow = {
  date: string;
  animal_type: string;
  total_in: number;
  total_out: number;
  net: number;
};

export type EventQuery = {
  limit?: number;
  offset?: number;
  camera_id?: number;
  direction?: Direction;
  animal_type?: string;
  from?: string;
  to?: string;
};

export type StatsMessage = {
  type: "statistics";
  in: number;
  out: number;
  current: number;
  camera: string;
  ai: string;
};

export type EventMessage = { type: "event"; event: EventRow };
export type LiveMessage = StatsMessage | EventMessage;
