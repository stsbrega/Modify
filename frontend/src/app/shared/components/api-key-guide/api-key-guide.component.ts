import { Component, input, signal } from '@angular/core';
import { LlmProvider } from '../../models/mod.model';

@Component({
  selector: 'app-api-key-guide',
  standalone: true,
  template: `
    <div class="guide-wrapper">
      <button class="guide-toggle" (click)="expanded.set(!expanded())" type="button">
        <svg class="guide-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        Need help finding API keys?
        <svg class="chevron" [class.expanded]="expanded()" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6 9l6 6 6-6"/>
        </svg>
      </button>

      @if (expanded()) {
        <div class="guide-body">
          <section class="guide-section">
            <h4>What are API keys?</h4>
            <p>
              API keys let ModdersOmni communicate with AI providers to generate your modlist.
              Each provider offers its own key — you paste it here, and we handle the rest.
            </p>
          </section>

          <section class="guide-section">
            <h4>Recommended providers</h4>
            <p class="tier-label free">Free tier available</p>
            <div class="provider-table">
              @for (p of freeProviders(); track p.id) {
                <div class="provider-row">
                  <span class="provider-name">{{ p.name }}</span>
                  <span class="provider-note">{{ getNote(p.id) }}</span>
                  <a class="provider-link" [href]="'https://' + p.hint_url" target="_blank" rel="noopener">
                    Get API Key
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/>
                    </svg>
                  </a>
                </div>
              }
            </div>

            <p class="tier-label paid">Paid</p>
            <div class="provider-table">
              @for (p of paidProviders(); track p.id) {
                <div class="provider-row">
                  <span class="provider-name">{{ p.name }}</span>
                  <span class="provider-note">{{ getNote(p.id) }}</span>
                  <a class="provider-link" [href]="'https://' + p.hint_url" target="_blank" rel="noopener">
                    Get API Key
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/>
                    </svg>
                  </a>
                </div>
              }
            </div>
          </section>

          <section class="guide-section">
            <h4>Why add multiple keys?</h4>
            <p>
              During modlist generation, if one provider hits a rate limit or encounters an error,
              ModdersOmni automatically switches to your next configured provider. More keys
              means more resilient, uninterrupted generation.
            </p>
          </section>
        </div>
      }
    </div>
  `,
  styles: [`
    .guide-wrapper {
      margin: 0.5rem 0 0.75rem;
    }

    .guide-toggle {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      background: none;
      border: none;
      color: var(--color-text-muted, #9a8c7a);
      font-size: 0.8rem;
      cursor: pointer;
      padding: 0.25rem 0;
      transition: color 0.2s;

      &:hover {
        color: var(--color-text, #e8dcc8);
      }
    }

    .guide-icon {
      opacity: 0.7;
    }

    .chevron {
      transition: transform 0.2s;
      margin-left: auto;

      &.expanded {
        transform: rotate(180deg);
      }
    }

    .guide-body {
      margin-top: 0.5rem;
      padding: 0.75rem;
      border: 1px solid var(--color-border, rgba(255 255 255 / 0.08));
      border-radius: 0.5rem;
      background: var(--color-surface-alt, rgba(255 255 255 / 0.02));
    }

    .guide-section {
      &:not(:last-child) {
        margin-bottom: 0.75rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--color-border, rgba(255 255 255 / 0.06));
      }

      h4 {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--color-text, #e8dcc8);
        margin: 0 0 0.35rem;
      }

      p {
        font-size: 0.75rem;
        color: var(--color-text-muted, #9a8c7a);
        line-height: 1.5;
        margin: 0;
      }
    }

    .tier-label {
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin: 0.5rem 0 0.25rem;

      &.free {
        color: var(--color-success, #4ade80);
      }

      &.paid {
        color: var(--color-text-muted, #9a8c7a);
      }
    }

    .provider-table {
      display: flex;
      flex-direction: column;
      gap: 0.3rem;
    }

    .provider-row {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.3rem 0.5rem;
      border-radius: 0.35rem;
      background: var(--color-surface, rgba(255 255 255 / 0.03));
    }

    .provider-name {
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--color-text, #e8dcc8);
      min-width: 5.5rem;
    }

    .provider-note {
      font-size: 0.7rem;
      color: var(--color-text-muted, #9a8c7a);
      flex: 1;
    }

    .provider-link {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      font-size: 0.7rem;
      color: var(--color-accent, #c4a050);
      text-decoration: none;
      white-space: nowrap;

      &:hover {
        text-decoration: underline;
      }
    }
  `],
})
export class ApiKeyGuideComponent {
  providers = input.required<LlmProvider[]>();
  expanded = signal(false);

  private readonly FREE_IDS = new Set(['groq', 'gemini', 'together']);
  private readonly NOTES: Record<string, string> = {
    groq: 'Fast inference, generous free tier',
    gemini: 'Free quota, good quality',
    together: 'Free models available',
    anthropic: 'Claude — highest quality',
    openai: 'GPT-4o — widely used',
    deepseek: 'Very affordable pricing',
    mistral: 'European provider, strong models',
  };

  freeProviders() {
    return this.providers().filter((p) => this.FREE_IDS.has(p.id));
  }

  paidProviders() {
    return this.providers().filter((p) => !this.FREE_IDS.has(p.id));
  }

  getNote(id: string): string {
    return this.NOTES[id] ?? '';
  }
}
