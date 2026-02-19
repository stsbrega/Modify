export interface UserHardware {
  gpu_model?: string;
  cpu_model?: string;
  ram_gb?: number;
  vram_mb?: number;
  cpu_cores?: number;
  cpu_speed_ghz?: number;
  hardware_tier?: string;
  hardware_raw_text?: string;
}

export interface User {
  id: string;
  email: string;
  email_verified: boolean;
  display_name?: string;
  avatar_url?: string;
  auth_provider: 'local' | 'google' | 'discord';
  hardware?: UserHardware;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface HardwareUpdateRequest {
  gpu_model?: string;
  cpu_model?: string;
  ram_gb?: number;
  vram_mb?: number;
  cpu_cores?: number;
  cpu_speed_ghz?: number;
  hardware_raw_text?: string;
}
