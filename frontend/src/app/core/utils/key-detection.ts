import { LlmProvider } from '../../shared/models/mod.model';

export interface DetectionResult {
  providerId: string;
  providerName: string;
  confidence: 'exact' | 'ambiguous';
  /** All matching provider IDs (>1 when ambiguous) */
  matchedProviders: { id: string; name: string }[];
}

/**
 * Auto-detect which LLM provider an API key belongs to based on known prefixes.
 *
 * Uses longest-prefix-match: `sk-ant-` uniquely matches Anthropic even though
 * `sk-` also matches OpenAI and DeepSeek. When the longest matching prefix is
 * shared by multiple providers (e.g., bare `sk-` → OpenAI + DeepSeek), the
 * result is marked `ambiguous` so the UI can prompt the user to choose.
 */
export function detectProvider(
  key: string,
  providers: LlmProvider[],
): DetectionResult | null {
  const trimmed = key.trim();
  if (!trimmed) return null;

  // Build a flat list of (prefix, providerId, providerName) sorted by prefix
  // length descending so we check longest prefixes first.
  const entries: { prefix: string; id: string; name: string }[] = [];
  for (const p of providers) {
    for (const prefix of p.key_prefixes) {
      entries.push({ prefix, id: p.id, name: p.name });
    }
  }
  entries.sort((a, b) => b.prefix.length - a.prefix.length);

  // Find the longest prefix that matches
  let bestLength = 0;
  const matched: { id: string; name: string }[] = [];

  for (const entry of entries) {
    if (entry.prefix.length < bestLength) {
      // We've already found a longer match — skip shorter ones
      break;
    }
    if (trimmed.startsWith(entry.prefix)) {
      bestLength = entry.prefix.length;
      // Avoid duplicate provider entries (a provider might match via
      // multiple prefixes of different lengths, but we only care about
      // the longest match tier)
      if (!matched.some((m) => m.id === entry.id)) {
        matched.push({ id: entry.id, name: entry.name });
      }
    }
  }

  if (matched.length === 0) return null;

  if (matched.length === 1) {
    return {
      providerId: matched[0].id,
      providerName: matched[0].name,
      confidence: 'exact',
      matchedProviders: matched,
    };
  }

  // Multiple providers share the same longest-matching prefix
  return {
    providerId: matched[0].id,
    providerName: matched[0].name,
    confidence: 'ambiguous',
    matchedProviders: matched,
  };
}
