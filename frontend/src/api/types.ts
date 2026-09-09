export type Role = "admin" | "viewer";
export type Direction = "IN" | "OUT";
export type InsideDirection = "UP" | "DOWN" | "LEFT" | "RIGHT";
export type CameraStatus = "ONLINE" | "OFFLINE" | "RECONNECTING";
export type AiStatus = "ACTIVE" | "IDLE";
export type WorkerState = "starting" | "running" | "restarting" | "stopped" | "failed";
export type InventoryHealth = "ok" | "mismatch" | "unconfigured";

export type LoginResponse = { access_token: string; token_type: string; role: Role };
export type Me = { id: number; username: string; role: Role; is_active: boolean };

export type SystemStatus = {
  camera: CameraStatus | string;
  ai: AiStatus | string;
  worker: WorkerState | string;
  restarts: number;
  last_error: string | null;
  inventory_health: InventoryHealth | string;
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
  line2_p1_x: number | null;
  line2_p1_y: number | null;
  line2_p2_x: number | null;
  line2_p2_y: number | null;
  inside_direction: InsideDirection | null;
  confidence: number | null;
  iou: number | null;
  frame_skip: number | null;
  stream_fps: number | null;
  inside_zone_id: number | null;
  outside_zone_id: number | null;
  created_at: string;
};

export type CameraInput = Omit<Camera, "id" | "created_at">;

export type AppSettings = {
  default_language: string;
  telegram_configured: boolean;
  telegram_aggregation_seconds: number;
  telegram_digest_hour: number | null;
  telegram_idle_hours: number | null;
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
  telegram_digest_hour: number | null;
  telegram_idle_hours: number | null;
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

export type ZoneKind = "PEN" | "PASTURE" | "QUARANTINE" | "EXTERNAL";
export type FarmZone = {
  id: number;
  name: string;
  kind: ZoneKind;
  is_active: boolean;
  sort_order: number;
  created_at: string;
};
export type AnimalSpecies = "sheep" | "cattle" | "goat" | "horse";
export type AnimalGroup = {
  id: number;
  name: string;
  species: AnimalSpecies;
  is_default_for_species: boolean;
  is_active: boolean;
  sort_order: number;
  created_at: string;
};
export type InventoryBalance = {
  zone_id: number;
  zone_name: string;
  group_id: number;
  group_name: string;
  species: AnimalSpecies;
  quantity: number;
};
export type MovementKind = "INITIAL" | "CAMERA" | "MANUAL_ADJUSTMENT" | "TRANSFER";
export type InventoryMovement = {
  id: number;
  group_id: number;
  from_zone_id: number | null;
  to_zone_id: number | null;
  quantity: number;
  kind: MovementKind;
  source_event_id: number | null;
  note: string;
  created_at: string;
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
