# Smart Dispatch: Credits + Managed LLM Routing

## Overview

Replace the current BYOK-only model with a dual-mode system: users can either bring their own API keys (existing behavior) or purchase ModdersOmni credits to use premium models without managing keys. A smart dispatcher routes each generation phase to the optimal model based on the user's tier and phase complexity.

## Business Model

### Tiers

| Tier | Cost | What You Get |
|------|------|-------------|
| **Free** | $0 | OpenRouter free models (rate-limited: 20 req/min, 200 req/day). ~5-10 generations/day. |
| **BYOK** | $0 (user pays providers directly) | Use your own API keys from any of the 9 supported providers. No limits beyond provider rate limits. |
| **Credits** | Pay-as-you-go via Stripe | Purchase credits ($5, $10, $25 packs). Server-side premium models (Claude, GPT-4o, Qwen3.5-Plus). Per-generation cost based on actual token usage. |
| **Pro (future)** | $X/month subscription | Monthly credit allotment + priority routing + faster models. |

### Revenue Flow

```
User buys $10 credit pack via Stripe
  → ModdersOmni stores credits in user account
  → User starts generation
  → Smart Dispatcher picks model per-phase
  → Token usage tracked from API response (usage.prompt_tokens, usage.completion_tokens)
  → Credits deducted based on token cost
  → If credits run out mid-generation, fall back to free tier or pause
```

---

## Architecture

### Phase 1: Credit System (Backend)

#### 1.1 Database Models

**File**: `backend/app/models/credit.py` (new)

```python
class CreditBalance(Base):
    __tablename__ = "credit_balances"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    balance_cents: Mapped[int] = mapped_column(default=0)  # Credits in cents (1 credit = 1 cent = ~1K tokens)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    amount_cents: Mapped[int]  # Positive = purchase, negative = usage
    type: Mapped[str]  # "purchase", "generation_usage", "refund", "bonus"
    description: Mapped[str | None]
    generation_id: Mapped[str | None]  # Links to the generation that consumed credits
    stripe_payment_id: Mapped[str | None]  # Links to Stripe for purchases
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

#### 1.2 Credit Service

**File**: `backend/app/services/credit_service.py` (new)

```python
class CreditService:
    async def get_balance(user_id: int) -> int
    async def add_credits(user_id: int, amount_cents: int, stripe_payment_id: str) -> CreditBalance
    async def deduct_credits(user_id: int, amount_cents: int, generation_id: str) -> CreditBalance
    async def has_sufficient_credits(user_id: int, estimated_cost: int) -> bool
    async def estimate_generation_cost(phases: int, model_tier: str) -> int
    async def get_transaction_history(user_id: int, limit: int = 50) -> list[CreditTransaction]
```

#### 1.3 Stripe Integration

**File**: `backend/app/api/credits.py` (new)

```
POST /api/credits/purchase          — Create Stripe Checkout session for credit pack
POST /api/credits/webhook           — Stripe webhook: payment succeeded → add credits
GET  /api/credits/balance           — Get current balance + recent transactions
GET  /api/credits/estimate          — Estimate cost for a generation (phases × model tier)
```

Credit packs:
- Starter: $5 → 500 credits
- Standard: $10 → 1,100 credits (10% bonus)
- Power: $25 → 3,000 credits (20% bonus)

#### 1.4 Token-to-Credit Conversion

After each LLM API call, extract `usage.prompt_tokens` and `usage.completion_tokens` from the response and convert to credits:

```python
def tokens_to_credits(prompt_tokens: int, completion_tokens: int, model_tier: str) -> int:
    """Convert token usage to credit cost in cents."""
    rates = {
        "free": 0,
        "budget": 0.5,   # ~$0.50 per 1M tokens (Groq, Qwen, DeepSeek)
        "standard": 2.0,  # ~$2 per 1M tokens (GPT-4o-mini, Gemini Flash)
        "premium": 8.0,   # ~$8 per 1M tokens (Claude Sonnet, GPT-4o)
    }
    rate = rates.get(model_tier, 2.0)
    total_tokens = prompt_tokens + (completion_tokens * 3)  # Output tokens cost ~3x input
    return int((total_tokens / 1_000_000) * rate * 100)  # Convert to cents
```

---

### Phase 2: Smart Dispatcher

#### 2.1 Model Tier Classification

**File**: `backend/app/llm/dispatcher.py` (new)

Each model in the registry gets a `tier` field:

```python
MODEL_TIERS = {
    # Free tier (no credits needed)
    "openrouter/free": "free",
    # Budget tier (~$0.10-0.50/M tokens)
    "llama-3.3-70b-versatile": "budget",       # Groq
    "qwen3.5-plus": "budget",                   # Qwen (DashScope is very cheap)
    "deepseek-chat": "budget",                   # DeepSeek
    # Standard tier (~$1-3/M tokens)
    "gemini-2.0-flash": "standard",              # Gemini
    "mistral-large-latest": "standard",          # Mistral
    "gpt-4o-mini": "standard",                   # OpenAI (mini)
    # Premium tier (~$5-15/M tokens)
    "claude-sonnet-4-20250514": "premium",       # Anthropic
    "gpt-4o": "premium",                         # OpenAI
}
```

#### 2.2 Phase Complexity Mapping

Not all 13 build phases need the same model quality:

```python
PHASE_COMPLEXITY = {
    # Simple phases — budget models handle fine
    "essentials": "low",       # Well-known required mods, minimal reasoning
    "ui": "low",               # Straightforward UI mod selection
    "bug_fixes": "low",        # Known patches, formulaic
    # Medium phases — standard models recommended
    "textures": "medium",      # Needs to reason about VRAM budget
    "environment": "medium",   # Weather/lighting compatibility
    "audio": "medium",
    "animations": "medium",
    # Complex phases — premium models shine
    "gameplay": "high",        # Complex mod interactions, playstyle interpretation
    "combat": "high",          # Requires deep compatibility reasoning
    "quests": "high",          # Content selection based on user preference
    "compatibility": "high",   # Patch detection, conflict resolution
    "post_build_audit": "high", # Full modlist review, VRAM/plugin count checks
}
```

#### 2.3 Dispatch Logic

```python
class SmartDispatcher:
    def select_model(
        self,
        user: User,
        phase: ModBuildPhase,
        available_keys: list[UserLlmKey],
        credit_balance: int,
    ) -> DispatchResult:
        """Pick the best model for this phase given user's resources."""

        complexity = PHASE_COMPLEXITY.get(phase.slug, "medium")

        # 1. If user has BYOK keys, prefer those (no credit cost)
        if available_keys:
            return self._select_from_byok(available_keys, complexity)

        # 2. If user has credits, pick based on phase complexity
        if credit_balance > 0:
            if complexity == "high":
                return DispatchResult(model="claude-sonnet-4-20250514", tier="premium")
            elif complexity == "medium":
                return DispatchResult(model="gemini-2.0-flash", tier="standard")
            else:
                return DispatchResult(model="qwen3.5-plus", tier="budget")

        # 3. Fall back to free tier
        return DispatchResult(model="openrouter/free", tier="free")
```

---

### Phase 3: Frontend Integration

#### 3.1 Credits Page

**File**: `frontend/src/app/features/credits/` (new feature module)

- Credit balance display (header bar or settings)
- Purchase flow (redirects to Stripe Checkout, returns to success/cancel page)
- Transaction history table
- Generation cost estimator ("This build will cost ~15 credits")

#### 3.2 Generation UI Updates

**File**: `frontend/src/app/features/generation/`

- Show current model being used per-phase in the SSE stream
- If credits run out mid-generation, show a "Top up credits to continue with premium models, or continue with free models" prompt
- Pre-generation cost estimate: "Estimated cost: 12-18 credits (you have 45 remaining)"

#### 3.3 Settings Page Updates

**File**: `frontend/src/app/features/settings/`

- New "Credits & Billing" tab
- Credit balance + purchase buttons
- Toggle: "Use credits for generation" vs "Use my own API keys"
- Transaction history

---

### Phase 4: Generation Pipeline Integration

#### 4.1 Modify Generation Flow

**File**: `backend/app/services/generation/manager.py`

Before each phase:
1. Smart Dispatcher selects model
2. If using credits, check sufficient balance
3. Create LLM provider with selected model
4. After phase completes, extract token usage from response
5. Deduct credits based on actual usage
6. Emit `model_info` SSE event so frontend shows which model is active

#### 4.2 New SSE Event Types

```python
# Emitted at the start of each phase
emit("model_selected", {
    "phase": phase.slug,
    "model": "claude-sonnet-4-20250514",
    "tier": "premium",
    "estimated_cost": 3,  # credits
})

# Emitted after each phase
emit("credits_used", {
    "phase": phase.slug,
    "tokens_used": 4521,
    "credits_deducted": 2,
    "remaining_balance": 43,
})
```

---

## Implementation Order

1. **Credit models + migration** — CreditBalance, CreditTransaction tables
2. **Credit service** — balance, add, deduct, estimate
3. **Stripe integration** — checkout session, webhook, credit packs
4. **Credits API endpoints** — purchase, balance, history, estimate
5. **Smart Dispatcher** — model selection logic, phase complexity mapping
6. **Generation pipeline integration** — token tracking, credit deduction, model switching
7. **Frontend: Credits page** — purchase flow, balance display, transaction history
8. **Frontend: Generation UI** — model info per-phase, cost estimates, mid-generation prompts
9. **Frontend: Settings tab** — Credits & Billing section

## Files Modified/Created

| File | Change |
|------|--------|
| `backend/app/models/credit.py` | **New** — CreditBalance, CreditTransaction models |
| `backend/app/services/credit_service.py` | **New** — Credit balance management |
| `backend/app/api/credits.py` | **New** — Purchase, webhook, balance endpoints |
| `backend/app/llm/dispatcher.py` | **New** — Smart model selection per-phase |
| `backend/app/llm/registry.py` | Add `tier` field to each provider entry |
| `backend/app/services/generation/manager.py` | Integrate dispatcher + token tracking |
| `backend/app/services/generation/modlist_generator.py` | Extract token usage after each API call |
| `backend/app/models/user.py` | Add `credit_balance` relationship |
| `backend/app/seeds/run_seed.py` | Add migration for credit tables |
| `backend/app/config.py` | Add Stripe keys, credit pack config |
| `backend/app/main.py` | Register credits router |
| `frontend/src/app/features/credits/` | **New** — Credits purchase + history page |
| `frontend/src/app/features/generation/` | Model info display, cost estimates |
| `frontend/src/app/features/settings/` | Credits & Billing tab |
| `frontend/src/app/core/services/` | CreditService for API calls |
| `frontend/src/app/shared/models/` | Credit TypeScript interfaces |

## Environment Variables (New)

```
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_STANDARD=price_...
STRIPE_PRICE_POWER=price_...
```
