export type SafetyLevel = 'Safe' | 'Sensitive' | 'NSFW' | 'Explicit';

export type ReasoningEffort = 'instruct' | 'off' | 'low' | 'medium' | 'high' | 'xhigh' | 'max' | 'on';

export interface Entity {
  id: string;
  name: string;
  source?: 'user_defined' | 'model_character' | null;
  canonical_tag?: string | null;
  caption_name?: string | null;
  custom_description?: string | null;
}

export interface Statement {
  kind: 'attribute' | 'relation' | 'scene' | 'general';
  subject?: string | null;
  target?: string | null;
  text: string;
  facet?: string | null;
  effect?: 'replace' | 'add' | 'modify' | null;
}

export interface SemanticFacts {
  entities: Entity[];
  statements: Statement[];
}

export interface Preset {
  id: number;
  name: string;
  positive_prefix: string;
  default_negative: string;
  is_default: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Character {
  id?: number;
  name: string;
  aliases?: string;
  gender?: string;
  age_group?: string;
  body?: string;
  hair_color?: string;
  hair_style?: string;
  hair_length?: string;
  eye_color?: string;
  facial_features?: string;
  headwear?: string;
  top?: string;
  outer?: string;
  bottom?: string;
  socks?: string;
  shoes?: string;
  accessories?: string;
  default_expression?: string;
  default_pose?: string;
  negative_traits?: string;
  extra_description?: string;
  category?: string;
  is_favorite: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Artist {
  id: number;
  name: string;
  tags: string;
  category: string;
  is_favorite: boolean;
  is_custom: boolean;
  preview_url?: string;
  description?: string;
}

export interface Lora {
  id: number;
  name: string;
  filename: string;
  trigger_words: string;
  default_strength: number;
  is_favorite: boolean;
  category: string;
  is_valid_file: boolean;
  source_path?: string | null;
  description?: string;
  cover_hidden?: boolean;

  // SHA256 本地缓存（LoRA Metadata V1）
  sha256?: string | null;
  sha256_file_size?: number | null;
  sha256_mtime_ns?: number | null;

  // Civitai 远端 metadata
  metadata_provider?: string | null;
  metadata_host?: string | null;
  metadata_status?: MetadataStatus | null;
  remote_model_id?: number | null;
  remote_version_id?: number | null;
  remote_file_id?: number | null;
  remote_model_name?: string | null;
  remote_version_name?: string | null;
  remote_file_name?: string | null;
  remote_base_model?: string | null;
  remote_trained_words?: string | null;   // JSON array 字符串（Civitai trainedWords 推荐）
  remote_description?: string | null;     // DEPRECATED 兼容字段（旧混合简介，新 UI 不依赖）
  remote_model_description?: string | null;   // 模型主页面简介（sanitized plain text）
  remote_version_description?: string | null; // 版本说明（sanitized plain text）
  // Civitai Usage Tips（Tier-2 enrichment，结构化值；绝不自动覆盖本地配置）
  remote_recommended_strength?: number | null;
  remote_clip_skip?: number | null;
  remote_steps?: number | null;
  remote_epochs?: number | null;
  remote_creator?: string | null;
  remote_tags?: string | null;            // JSON array 字符串
  remote_nsfw_level?: number | null;
  cached_cover_path?: string | null;
  metadata_fetched_at?: string | null;
  metadata_json?: string | null;
}

export type MetadataStatus =
  | 'matched'
  | 'not_found'
  | 'remote_error'
  | 'rate_limited'
  | 'local_file_not_found'
  | 'local_file_ambiguous'
  | 'hash_file_mismatch'
  | null;

export interface LoraSource {
  id: number;
  display_path: string;
  resolved_path: string;
  enabled: boolean;
  recursive: boolean;
  created_at: string;
  exists: boolean;
  is_dir: boolean;
  readable: boolean;
  error?: string | null;
}

export interface ScanCandidate {
  relative_path: string;
  basename: string;
  full_path: string;
  name_hint: string;
  exists_in_db: boolean;
  comfy_recognized: boolean;
  comfy_name: string;
  basename_conflict: boolean;
}

export interface ScanSummary {
  total: number;
  already_imported: number;
  new: number;
  comfy_unrecognized: number;
  basename_conflicts: number;
  comfy_available: boolean;
}

export interface ScanResult {
  source: LoraSource;
  candidates: ScanCandidate[];
  summary: ScanSummary;
}

export interface RuleFile {
  id: number;
  name: string;
  file_type: string;
  content: string;
  is_enabled: boolean;
  sort_order: number;
}

export interface GenerationHistory {
  id: number;
  raw_input: string;
  parsed_facts_json: string;
  prompt: string;
  negative_prompt: string;
  safety: string;
  artists_json: string;
  loras_json: string;
  comfy_params_json: string;
  image_path?: string;
  created_at: string;
}

export interface AppSettings {
  ACTIVE_PROVIDER: 'lm_studio' | 'cloud';
  LM_STUDIO_BASE_URL: string;
  LM_STUDIO_API_KEY: string;
  LM_STUDIO_MODEL: string;
  LM_STUDIO_AUTO_LOAD: boolean;
  LM_STUDIO_AUTO_UNLOAD: boolean;

  CLOUD_API_NAME: string;
  CLOUD_API_BASE_URL: string;
  CLOUD_API_KEY: string;
  CLOUD_MODEL: string;

  COMFYUI_BASE_URL: string;
  DEFAULT_SAFETY: SafetyLevel;
  GENERATE_TIMEOUT_SECONDS: number;

  // 角色联网解析（Character Online Resolver V1）
  ONLINE_RESOLVE_ENABLED: boolean;
  ONLINE_RESOLVE_CACHE_WRITE: boolean;
  ONLINE_RESOLVE_AMBIGUOUS: 'ask';

  // Civitai Metadata（LoRA Metadata V1）— 只允许 red / com 两个官方 host
  CIVITAI_API_HOST: 'red' | 'com';
  // 前端永远拿不到 token 明文（GET 只返回 CIVITAI_API_TOKEN_SET 布尔位）
  CIVITAI_API_TOKEN: string;
  CIVITAI_API_TOKEN_SET?: boolean;
}
