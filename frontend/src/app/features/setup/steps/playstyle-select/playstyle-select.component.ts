import { Component, EventEmitter, Input, OnInit, Output, signal, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../../../core/services/api.service';
import { AuthService } from '../../../../core/services/auth.service';
import { GenerationService } from '../../../../core/services/generation.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { Playstyle } from '../../../../shared/models/game.model';
import { HardwareSpecs } from '../../../../shared/models/specs.model';
import { LlmProvider } from '../../../../shared/models/mod.model';
import { detectProvider } from '../../../../core/utils/key-detection';
import { ApiKeyGuideComponent } from '../../../../shared/components/api-key-guide/api-key-guide.component';
import { trigger, transition, style, animate, query, stagger } from '@angular/animations';

@Component({
  selector: 'app-playstyle-select',
  standalone: true,
  imports: [FormsModule, ApiKeyGuideComponent],
  animations: [
    trigger('staggerCards', [
      transition(':enter', [
        query('.playstyle-card', [
          style({ opacity: 0, transform: 'translateY(12px)' }),
          stagger(60, [
            animate('350ms cubic-bezier(0.16, 1, 0.3, 1)', style({ opacity: 1, transform: 'translateY(0)' })),
          ]),
        ], { optional: true }),
      ]),
    ]),
  ],
  template: `
    <div class="playstyle-select">
      <h2>Choose Your Playstyle</h2>
      <p class="step-desc">
        Select the experience you want. Your hardware will be taken into account.
      </p>

      <div class="playstyles-grid" @staggerCards>
        @for (ps of playstyles(); track ps.id) {
          <button
            class="playstyle-card"
            [class.selected]="selectedId() === ps.id"
            (click)="select(ps.id)"
          >
            <div class="ps-icon">{{ ps.icon || ps.name.charAt(0) }}</div>
            <div class="ps-content">
              <h3>{{ ps.name }}</h3>
              @if (ps.description) {
                <p>{{ ps.description }}</p>
              }
            </div>
            @if (selectedId() === ps.id) {
              <div class="ps-check">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
            }
          </button>
        }
        @if (playstyles().length === 0) {
          <div class="loading-state">
            <span class="load-spinner"></span>
            Loading playstyles...
          </div>
        }
      </div>

      <!-- Nexus Mods API Key Section -->
      <div class="nexus-key-section" [class.pending-highlight]="pendingNexusKey()">
        <div class="provider-header" (click)="nexusExpanded.set(!nexusExpanded())">
          <div class="provider-label">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
            </svg>
            Nexus Mods API Key
          </div>
          @if (isLoggedIn()) {
            <div class="provider-badge" [class.configured]="nexusKey()">
              {{ nexusKey() ? 'Configured' : 'Not configured' }}
            </div>
          } @else {
            <div class="provider-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              Account required
            </div>
          }
          <svg class="chevron" [class.expanded]="nexusExpanded()" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 9l6 6 6-6"/>
          </svg>
        </div>

        @if (nexusExpanded()) {
          <div class="provider-body">
            @if (!isLoggedIn()) {
              <div class="locked-message">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <p>Create an account to add your Nexus Mods API key and generate your modlist.</p>
              </div>
            } @else {
              @if (pendingNexusKey()) {
                <p class="pending-prompt">
                  A Nexus Mods API key is required to search and download mods. Enter your key below.
                </p>
              } @else {
                <p class="provider-desc">
                  Required for live mod searching and downloads from Nexus Mods.
                </p>
              }

              <div class="nexus-key-row" [class.has-key]="nexusKey()">
                <div class="key-input-wrap">
                  <input
                    [type]="nexusKeyVisible() ? 'text' : 'password'"
                    [value]="nexusKey()"
                    (input)="onNexusKeyInput($event)"
                    placeholder="Nexus Mods Personal API Key"
                    autocomplete="off"
                    spellcheck="false"
                  />
                  <button class="key-toggle" (click)="nexusKeyVisible.set(!nexusKeyVisible())" type="button" tabindex="-1">
                    @if (nexusKeyVisible()) {
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                        <line x1="1" y1="1" x2="23" y2="23"/>
                      </svg>
                    } @else {
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                      </svg>
                    }
                  </button>
                </div>
              </div>

              <div class="nexus-guide">
                <p class="guide-title">How to get your API key:</p>
                <ol class="guide-steps">
                  <li>Log in at <strong>nexusmods.com</strong></li>
                  <li>Click your <strong>profile icon</strong> (top right)</li>
                  <li>Select <strong>Site Preferences</strong></li>
                  <li>Click <strong>API Keys</strong></li>
                  <li>Scroll to the bottom and copy your <strong>Personal API Key</strong></li>
                </ol>
                <a class="nexus-link" href="https://next.nexusmods.com/settings/api-keys" target="_blank" rel="noopener">
                  Open Nexus API Keys Page
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/>
                  </svg>
                </a>
              </div>
            }
          </div>
        }
      </div>

      <div class="ai-provider-section" [class.pending-highlight]="pendingGenerate()">
        <div class="provider-header" (click)="providerExpanded.set(!providerExpanded())">
          <div class="provider-label">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 2a4 4 0 0 1 4 4v1a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4zM18 14h.01M6 14h.01M15 18s-1 2-3 2-3-2-3-2"/>
              <rect x="3" y="11" width="18" height="10" rx="2"/>
            </svg>
            AI Providers
          </div>
          @if (isLoggedIn()) {
            <div class="provider-badge" [class.configured]="configuredCount() > 0">
              {{ configuredCount() }} configured
            </div>
          } @else {
            <div class="provider-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              Account required
            </div>
          }
          <svg class="chevron" [class.expanded]="providerExpanded()" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 9l6 6 6-6"/>
          </svg>
        </div>

        @if (providerExpanded()) {
          <div class="provider-body">
            @if (!isLoggedIn()) {
              <div class="locked-message">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <p>Create an account to configure AI providers and generate your modlist.</p>
              </div>
            } @else {
              @if (pendingGenerate()) {
                <p class="pending-prompt">
                  Enter at least one API key below, then generation will start automatically.
                </p>
              } @else {
                <p class="provider-desc">
                  Paste an API key — the provider will be detected automatically.
                </p>
              }

              <div class="key-security-notice">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <span>Keys are stored securely and never shared. You can remove them anytime.</span>
              </div>

              <app-api-key-guide [providers]="providers()" />

              <!-- Add Key Input -->
              <div class="add-key-row">
                <div class="key-input-wrap">
                  <input
                    type="password"
                    [value]="newKeyInput()"
                    (input)="newKeyInput.set($any($event.target).value)"
                    (paste)="onNewKeyPaste($event)"
                    placeholder="Paste any AI provider API key..."
                    autocomplete="off"
                    spellcheck="false"
                  />
                </div>
                <button class="btn-add-key" (click)="addNewKey()" [disabled]="!newKeyInput()">
                  Add
                </button>
              </div>

              <!-- Detection feedback -->
              @if (detectionState()) {
                <div class="detection-feedback" [class.warn]="detectionState()!.type !== 'exact'">
                  @if (detectionState()!.type === 'exact') {
                    <div class="detection-exact">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                      Detected: <strong>{{ detectionState()!.providerName }}</strong>
                    </div>
                  } @else if (detectionState()!.type === 'ambiguous') {
                    <div class="detection-warn-msg">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="8" x2="12" y2="12"/>
                        <line x1="12" y1="16" x2="12.01" y2="16"/>
                      </svg>
                      <span>Multiple providers match. Select one:</span>
                    </div>
                    <select class="detect-select" (change)="confirmDetectedProvider($any($event.target).value)">
                      <option value="" disabled selected>Select...</option>
                      @for (m of detectionState()!.matches; track m.id) {
                        <option [value]="m.id">{{ m.name }}</option>
                      }
                    </select>
                  } @else {
                    <div class="detection-warn-msg">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="8" x2="12" y2="12"/>
                        <line x1="12" y1="16" x2="12.01" y2="16"/>
                      </svg>
                      <span>Unknown key format. Select provider:</span>
                    </div>
                    <select class="detect-select" (change)="confirmDetectedProvider($any($event.target).value)">
                      <option value="" disabled selected>Select...</option>
                      @for (p of providers(); track p.id) {
                        <option [value]="p.id">{{ p.name }}</option>
                      }
                    </select>
                  }
                </div>
              }

              <!-- Saved Keys -->
              @if (savedKeyEntries().length > 0) {
                <div class="saved-keys-list">
                  @for (entry of savedKeyEntries(); track entry.providerId) {
                    <div class="saved-key-chip">
                      <span class="chip-provider">{{ entry.providerName }}</span>
                      <span class="chip-mask">{{ entry.masked }}</span>
                      <button class="chip-remove" (click)="removeKey(entry.providerId)" title="Remove">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                      </button>
                    </div>
                  }
                </div>
              } @else if (providers().length === 0) {
                <div class="loading-state">
                  <span class="load-spinner"></span>
                  Loading providers...
                </div>
              }
            }
          </div>
        }
      </div>

      <div class="actions">
        <button class="btn-back" (click)="back.emit()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          Back
        </button>
        <button
          class="btn-primary"
          (click)="generate()"
          [disabled]="!selectedId() || loading()"
        >
          @if (loading()) {
            <span class="btn-spinner"></span>
            Generating...
          } @else {
            Generate Modlist
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          }
        </button>
      </div>
    </div>
  `,
  styles: [`
    .playstyle-select {
      max-width: 640px;
      margin: 0 auto;
    }
    h2 {
      font-size: 1.25rem;
      font-weight: 600;
      margin-bottom: 0.375rem;
      text-align: center;
    }
    .step-desc {
      font-size: 0.875rem;
      color: var(--color-text-muted);
      text-align: center;
      margin-bottom: 2rem;
    }
    .playstyles-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
      gap: 0.75rem;
      margin-bottom: 2rem;
    }
    .playstyle-card {
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      background: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: 10px;
      padding: 1rem 1.125rem;
      text-align: left;
      cursor: pointer;
      color: var(--color-text);
      font-family: inherit;
      transition: border-color 0.15s, background 0.15s, transform 0.15s;
      position: relative;
    }
    .playstyle-card:hover {
      border-color: var(--color-border-hover);
      transform: translateY(-1px);
    }
    .playstyle-card.selected {
      border-color: var(--color-gold);
      background: rgba(192, 160, 96, 0.05);
    }
    .ps-icon {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--color-border);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1rem;
      font-weight: 600;
      flex-shrink: 0;
    }
    .playstyle-card.selected .ps-icon {
      background: rgba(192, 160, 96, 0.12);
      border-color: rgba(192, 160, 96, 0.3);
      color: var(--color-gold);
    }
    .ps-content {
      flex: 1;
      min-width: 0;
    }
    .ps-content h3 {
      font-size: 0.875rem;
      font-weight: 600;
      margin: 0 0 0.25rem;
    }
    .ps-content p {
      font-size: 0.75rem;
      color: var(--color-text-muted);
      line-height: 1.4;
      margin: 0;
    }
    .ps-check {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: var(--color-gold);
      color: #0D0D0F;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .loading-state {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      padding: 2rem;
      color: var(--color-text-muted);
      font-size: 0.875rem;
    }
    .load-spinner {
      width: 16px;
      height: 16px;
      border: 2px solid var(--color-border);
      border-top-color: var(--color-gold);
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
    }

    /* Actions */
    .actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }
    .btn-back {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      background: none;
      border: none;
      color: var(--color-text-muted);
      font-size: 0.8125rem;
      font-weight: 500;
      padding: 0.5rem 0;
      cursor: pointer;
      transition: color 0.15s;
    }
    .btn-back:hover { color: var(--color-text); }
    .btn-primary {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: var(--color-gold);
      color: #0D0D0F;
      padding: 0.625rem 1.5rem;
      border-radius: 8px;
      font-weight: 600;
      border: none;
      cursor: pointer;
      font-size: 0.875rem;
      transition: background 0.2s, box-shadow 0.3s;
    }
    .btn-primary:hover {
      background: var(--color-gold-hover);
      box-shadow: 0 0 20px var(--color-gold-glow);
    }
    .btn-primary:disabled {
      opacity: 0.4;
      cursor: not-allowed;
      box-shadow: none;
    }
    .btn-spinner {
      width: 14px;
      height: 14px;
      border: 2px solid rgba(13, 13, 15, 0.3);
      border-top-color: #0D0D0F;
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* AI Provider Section */
    .ai-provider-section {
      background: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: 10px;
      margin-bottom: 1.5rem;
      overflow: hidden;
      transition: border-color 0.3s;
    }
    .ai-provider-section.pending-highlight {
      border-color: var(--color-gold);
    }
    .provider-header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.875rem 1.125rem;
      cursor: pointer;
      transition: background 0.15s;
    }
    .provider-header:hover { background: rgba(255,255,255,0.02); }
    .provider-label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--color-text);
    }
    .provider-badge {
      margin-left: auto;
      font-size: 0.75rem;
      padding: 0.2rem 0.625rem;
      border-radius: 100px;
      background: rgba(255,255,255,0.04);
      color: var(--color-text-muted);
      border: 1px solid var(--color-border);
    }
    .provider-badge.configured {
      background: rgba(192, 160, 96, 0.1);
      color: var(--color-gold);
      border-color: rgba(192, 160, 96, 0.25);
    }
    .chevron {
      color: var(--color-text-muted);
      transition: transform 0.2s;
      flex-shrink: 0;
    }
    .chevron.expanded { transform: rotate(180deg); }
    .provider-body {
      padding: 0 1.125rem 1.125rem;
    }
    .provider-desc {
      font-size: 0.8125rem;
      color: var(--color-text-muted);
      line-height: 1.5;
      margin: 0 0 1rem;
    }
    .pending-prompt {
      font-size: 0.8125rem;
      color: var(--color-gold);
      line-height: 1.5;
      margin: 0 0 1rem;
      font-weight: 500;
    }
    .locked-message {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--color-border);
      border-radius: 8px;
      color: var(--color-text-muted);
    }
    .locked-message svg {
      flex-shrink: 0;
      color: var(--color-text-dim);
    }
    .locked-message p {
      font-size: 0.8125rem;
      line-height: 1.5;
      margin: 0;
    }

    /* Provider list (vertical rows) */
    .provider-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .provider-row {
      display: flex;
      flex-direction: column;
      gap: 0.375rem;
      padding: 0.75rem;
      background: rgba(255,255,255,0.015);
      border: 1px solid var(--color-border);
      border-radius: 8px;
      transition: border-color 0.15s;
    }
    .provider-row.has-key {
      border-color: rgba(192, 160, 96, 0.3);
    }
    .provider-info {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .provider-status {
      width: 20px;
      height: 20px;
      border-radius: 50%;
      border: 1.5px solid var(--color-border);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      color: var(--color-text-dim);
    }
    .provider-row.has-key .provider-status {
      background: var(--color-gold);
      border-color: var(--color-gold);
      color: #0D0D0F;
    }
    .provider-name {
      font-size: 0.8125rem;
      font-weight: 600;
      margin-right: 0.5rem;
    }
    .provider-model {
      font-size: 0.6875rem;
      color: var(--color-text-muted);
    }
    .key-input-wrap {
      display: flex;
      align-items: center;
      background: var(--color-bg);
      border: 1px solid var(--color-border);
      border-radius: 6px;
      overflow: hidden;
      transition: border-color 0.15s;
    }
    .key-input-wrap:focus-within {
      border-color: var(--color-gold);
    }
    .key-input-wrap input {
      flex: 1;
      background: none;
      border: none;
      color: var(--color-text);
      font-size: 0.75rem;
      padding: 0.5rem 0.625rem;
      outline: none;
      font-family: monospace;
      min-width: 0;
    }
    .key-input-wrap input::placeholder {
      color: var(--color-text-dim);
      font-family: inherit;
    }
    .key-toggle {
      background: none;
      border: none;
      color: var(--color-text-muted);
      padding: 0.375rem 0.625rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      flex-shrink: 0;
    }
    .key-toggle:hover { color: var(--color-text); }
    .key-hint {
      font-size: 0.6875rem;
      color: var(--color-text-dim);
    }

    /* Security notice */
    .key-security-notice {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.375rem 0.625rem;
      background: rgba(192, 160, 96, 0.06);
      border: 1px solid rgba(192, 160, 96, 0.12);
      border-radius: 6px;
      margin-bottom: 0.625rem;
      font-size: 0.6875rem;
      color: var(--color-text-dim);
      line-height: 1.3;
    }
    .key-security-notice svg {
      flex-shrink: 0;
      color: var(--color-gold);
    }

    /* Add key row */
    .add-key-row {
      display: flex;
      gap: 0.375rem;
      margin-bottom: 0.375rem;
    }
    .add-key-row .key-input-wrap { flex: 1; }
    .btn-add-key {
      background: var(--color-gold);
      color: #0D0D0F;
      padding: 0.375rem 0.75rem;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
      white-space: nowrap;
      transition: background 0.2s;
    }
    .btn-add-key:hover:not(:disabled) { background: var(--color-gold-hover); }
    .btn-add-key:disabled { opacity: 0.4; cursor: not-allowed; }

    /* Detection feedback */
    .detection-feedback {
      padding: 0.5rem 0.625rem;
      border-radius: 6px;
      margin-bottom: 0.5rem;
      font-size: 0.75rem;
      background: rgba(34, 197, 94, 0.08);
      border: 1px solid rgba(34, 197, 94, 0.2);
    }
    .detection-feedback.warn {
      background: rgba(234, 179, 8, 0.08);
      border: 1px solid rgba(234, 179, 8, 0.2);
    }
    .detection-exact {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      color: #22c55e;
      font-weight: 500;
    }
    .detection-exact strong { color: var(--color-text); }
    .detection-warn-msg {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      color: var(--color-warning);
      margin-bottom: 0.375rem;
    }
    .detection-warn-msg svg { flex-shrink: 0; }
    .detect-select {
      width: 100%;
      background: var(--color-bg);
      border: 1px solid var(--color-border);
      border-radius: 6px;
      color: var(--color-text);
      padding: 0.375rem 0.5rem;
      font-size: 0.75rem;
      outline: none;
      cursor: pointer;
    }
    .detect-select:focus { border-color: var(--color-gold); }

    /* Saved keys chips */
    .saved-keys-list {
      display: flex;
      flex-wrap: wrap;
      gap: 0.375rem;
      margin-top: 0.375rem;
    }
    .saved-key-chip {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.25rem 0.375rem 0.25rem 0.625rem;
      background: var(--color-bg);
      border: 1px solid var(--color-border);
      border-radius: 100px;
      font-size: 0.6875rem;
    }
    .chip-provider {
      font-weight: 600;
      color: var(--color-text);
    }
    .chip-mask {
      color: var(--color-text-dim);
      font-family: monospace;
      font-size: 0.625rem;
    }
    .chip-remove {
      background: none;
      border: none;
      color: var(--color-text-dim);
      padding: 0.125rem;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      transition: color 0.15s, background 0.15s;
    }
    .chip-remove:hover {
      color: #ef4444;
      background: rgba(239, 68, 68, 0.1);
    }

    /* Nexus Key Section */
    .nexus-key-section {
      background: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: 10px;
      margin-bottom: 0.75rem;
      overflow: hidden;
      transition: border-color 0.3s;
    }
    .nexus-key-section.pending-highlight {
      border-color: var(--color-gold);
    }
    .nexus-key-row {
      padding: 0.5rem 0;
    }
    .nexus-key-row.has-key .key-input-wrap {
      border-color: rgba(192, 160, 96, 0.3);
    }
    .nexus-guide {
      margin-top: 0.75rem;
      padding: 0.75rem;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--color-border);
      border-radius: 8px;
    }
    .guide-title {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--color-text-muted);
      margin: 0 0 0.5rem;
    }
    .guide-steps {
      margin: 0 0 0.625rem;
      padding-left: 1.25rem;
      font-size: 0.75rem;
      color: var(--color-text-muted);
      line-height: 1.7;
    }
    .guide-steps strong {
      color: var(--color-text);
      font-weight: 500;
    }
    .nexus-link {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      font-size: 0.75rem;
      color: var(--color-gold);
      text-decoration: none;
      font-weight: 500;
      transition: opacity 0.15s;
    }
    .nexus-link:hover {
      opacity: 0.8;
    }
  `],
})
export class PlaystyleSelectComponent implements OnInit {
  @Input() gameId!: number;
  @Input() specs!: HardwareSpecs;
  @Input() gameVersion: string | undefined;
  @Input() initialPlaystyleId?: number;
  @Output() back = new EventEmitter<void>();

  playstyles = signal<Playstyle[]>([]);
  selectedId = signal<number | null>(null);
  loading = signal(false);

  // Nexus Mods API key state
  nexusKey = signal('');
  nexusKeyVisible = signal(false);
  nexusExpanded = signal(true);
  pendingNexusKey = signal(false);

  // AI Provider state
  providers = signal<LlmProvider[]>([]);
  providerExpanded = signal(true);
  providerKeys = signal<Record<string, string>>({});
  pendingGenerate = signal(false);

  // Dynamic key entry state
  newKeyInput = signal('');
  detectionState = signal<{
    type: 'exact' | 'ambiguous' | 'unknown';
    providerId?: string;
    providerName?: string;
    matches?: { id: string; name: string }[];
  } | null>(null);
  savedKeyEntries = computed(() => {
    const keys = this.providerKeys();
    const providers = this.providers();
    return Object.entries(keys)
      .filter(([, key]) => key.length > 0)
      .map(([providerId, key]) => {
        const provider = providers.find(p => p.id === providerId);
        const masked = key.length > 12
          ? key.substring(0, 6) + '...' + key.substring(key.length - 4)
          : '***';
        return { providerId, providerName: provider?.name || providerId, masked };
      });
  });

  configuredCount = computed(() =>
    Object.values(this.providerKeys()).filter(k => k.length > 0).length
  );

  constructor(
    private api: ApiService,
    private authService: AuthService,
    private generationService: GenerationService,
    private notifications: NotificationService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.api.getPlaystyles(this.gameId).subscribe({
      next: (playstyles) => {
        this.playstyles.set(playstyles);
        // Auto-select playstyle if restored from wizard state
        if (this.initialPlaystyleId && playstyles.some(ps => ps.id === this.initialPlaystyleId)) {
          this.selectedId.set(this.initialPlaystyleId);
        }
      },
      error: () => {},
    });

    // Load provider registry from API
    this.api.getLlmProviders().subscribe({
      next: (providers) => this.providers.set(providers),
      error: () => {},
    });

    // Only load keys if logged in — guests don't see the key inputs
    if (this.authService.isLoggedIn()) {
      // Load Nexus key from user settings
      this.api.getSettings().subscribe({
        next: (settings: any) => {
          if (settings?.nexus_api_key) {
            this.nexusKey.set(settings.nexus_api_key);
            this.nexusExpanded.set(false);
          }
        },
        error: () => {},
      });

      let localKeys: Record<string, string> = {};
      try {
        const saved = localStorage.getItem('llm_keys');
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed && typeof parsed === 'object') localKeys = parsed;
        }
      } catch { /* ignore corrupt localStorage */ }

      this.api.getLlmKeys().subscribe({
        next: (profileKeys) => {
          const merged = { ...localKeys, ...profileKeys };
          this.providerKeys.set(merged);
          this.persistToLocalStorage(merged);
          if (Object.values(merged).some(k => k?.length > 0)) {
            this.providerExpanded.set(false);
          }
        },
        error: () => {
          this.providerKeys.set(localKeys);
          if (Object.values(localKeys).some(k => k?.length > 0)) {
            this.providerExpanded.set(false);
          }
        },
      });
    }
  }

  select(id: number): void {
    this.selectedId.set(id);
    this.pendingGenerate.set(false);
  }

  getKey(provider: string): string {
    return this.providerKeys()[provider] || '';
  }

  onNewKeyPaste(event: ClipboardEvent): void {
    const pasted = event.clipboardData?.getData('text')?.trim();
    if (!pasted) return;
    setTimeout(() => this.runKeyDetection(pasted), 0);
  }

  addNewKey(): void {
    const key = this.newKeyInput().trim();
    if (!key) return;
    const state = this.detectionState();
    if (state?.type === 'exact' && state.providerId) {
      this.saveAutoDetectedKey(state.providerId, key);
    } else if (!state) {
      this.runKeyDetection(key);
    }
  }

  confirmDetectedProvider(providerId: string): void {
    if (!providerId) return;
    const key = this.newKeyInput().trim();
    if (!key) return;
    this.saveAutoDetectedKey(providerId, key);
  }

  removeKey(providerId: string): void {
    const updated = { ...this.providerKeys() };
    delete updated[providerId];
    this.providerKeys.set(updated);
    this.persistToLocalStorage(updated);
    if (this.authService.isLoggedIn()) {
      this.api.saveLlmKeys({ [providerId]: '' }).subscribe({ error: () => {} });
    }
  }

  private runKeyDetection(key: string): void {
    const result = detectProvider(key, this.providers());
    if (!result) {
      this.detectionState.set({ type: 'unknown' });
    } else if (result.confidence === 'exact') {
      this.detectionState.set({
        type: 'exact',
        providerId: result.providerId,
        providerName: result.providerName,
      });
    } else {
      this.detectionState.set({
        type: 'ambiguous',
        matches: result.matchedProviders,
      });
    }
  }

  private saveAutoDetectedKey(providerId: string, key: string): void {
    const updated = { ...this.providerKeys(), [providerId]: key };
    this.providerKeys.set(updated);
    this.persistToLocalStorage(updated);

    if (this.authService.isLoggedIn()) {
      this.api.saveLlmKeys({ [providerId]: key }).subscribe({ error: () => {} });
    }

    // Reset input state
    this.newKeyInput.set('');
    this.detectionState.set(null);

    // Auto-resume generation if pending
    if (this.pendingGenerate() && this.configuredCount() > 0) {
      this.pendingGenerate.set(false);
      setTimeout(() => this.generate(), 100);
    }
  }

  onNexusKeyInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.nexusKey.set(value);

    // Persist to profile (fire-and-forget)
    if (this.authService.isLoggedIn()) {
      this.api.updateSettings({ nexus_api_key: value }).subscribe({
        error: () => {},
      });
    }

    // Auto-resume: if user was waiting to generate and now has Nexus key
    if (this.pendingNexusKey() && value.length > 0) {
      this.pendingNexusKey.set(false);
      setTimeout(() => this.generate(), 100);
    }
  }

  isLoggedIn(): boolean {
    return this.authService.isLoggedIn();
  }

  generate(): void {
    const playstyleId = this.selectedId();
    if (!playstyleId) return;

    // Auth check first — guests can't enter keys or generate
    if (!this.authService.isLoggedIn()) {
      this.saveWizardState(playstyleId);
      this.notifications.info('Create an account to generate your modlist');
      this.router.navigate(['/auth/register'], {
        queryParams: { returnUrl: '/setup' },
      });
      return;
    }

    // Nexus key check — required for mod searching/downloading
    if (!this.nexusKey()) {
      this.pendingNexusKey.set(true);
      this.nexusExpanded.set(true);
      return;
    }

    if (this.configuredCount() === 0) {
      this.pendingGenerate.set(true);
      this.providerExpanded.set(true);
      return;
    }

    // Build credentials list from all configured providers
    const allKeys = this.providerKeys();
    const credentials = Object.entries(allKeys)
      .filter(([, key]) => key.length > 0)
      .map(([provider, api_key]) => ({ provider, api_key }));

    this.loading.set(true);

    // Fire-and-redirect: POST /start returns immediately with a generation_id.
    // We then navigate to the generation viewer which streams events via SSE.
    this.api
      .startGeneration({
        game_id: this.gameId,
        playstyle_id: playstyleId,
        gpu: this.specs.gpu,
        vram_mb: this.specs.vram_mb,
        cpu: this.specs.cpu,
        ram_gb: this.specs.ram_gb,
        cpu_cores: this.specs.cpu_cores,
        cpu_speed_ghz: this.specs.cpu_speed_ghz,
        game_version: this.gameVersion,
        available_storage_gb: this.getMaxFreeStorageGb(),
        llm_credentials: credentials,
      })
      .subscribe({
        next: (response) => {
          this.loading.set(false);

          // Reset any stale generation state and open the SSE connection
          this.generationService.reset();
          this.generationService.connectToEvents(response.generation_id);

          // Navigate to the real-time generation viewer
          this.router.navigate(['/generate', response.generation_id]);
        },
        error: (err) => {
          this.loading.set(false);
          if (!err?.error?.detail && err?.status !== 0) {
            this.notifications.error('Failed to start generation. Check your API keys and try again.');
          }
        },
      });
  }

  private saveWizardState(playstyleId: number): void {
    const state = {
      gameId: this.gameId,
      gameVersion: this.gameVersion,
      specs: this.specs,
      playstyleId,
      timestamp: Date.now(),
    };
    localStorage.setItem('setup_wizard_state', JSON.stringify(state));
  }

  private persistToLocalStorage(keys: Record<string, string>): void {
    const toSave: Record<string, string> = {};
    for (const [k, v] of Object.entries(keys)) {
      if (v) toSave[k] = v;
    }
    localStorage.setItem('llm_keys', JSON.stringify(toSave));
  }

  private getMaxFreeStorageGb(): number | undefined {
    const drives = this.specs.storage_drives;
    if (!drives) return undefined;
    const matches = drives.match(/(\d+)\s*GB\s*free/gi);
    if (!matches?.length) return undefined;
    return Math.max(...matches.map(m => parseInt(m)));
  }
}
