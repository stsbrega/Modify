export interface ModEntry {
  mod_id?: number;
  nexus_mod_id?: number;
  name: string;
  author?: string;
  summary?: string;
  reason?: string;
  load_order?: number;
  is_patch?: boolean;
  patches_mods?: string[];
  compatibility_notes?: string;
}

export interface UserKnowledgeFlag {
  mod_a: string;
  mod_b: string;
  issue: string;
  severity: string; // "warning" | "critical"
}

export interface Modlist {
  id: string;
  game_id: number;
  game_domain?: string;
  playstyle_id: number;
  entries: ModEntry[];
  llm_provider?: string;
  user_knowledge_flags?: UserKnowledgeFlag[];
  used_fallback?: boolean;
  generation_error?: string;
  created_at?: string;
}

export interface LlmProvider {
  id: string;
  name: string;
  model: string;
  placeholder: string;
  hint_url: string;
  key_prefixes: string[];
}
