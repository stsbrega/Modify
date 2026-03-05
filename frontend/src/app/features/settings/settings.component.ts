import { Component, computed, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { trigger, transition, style, animate } from '@angular/animations';
import { ApiService } from '../../core/services/api.service';
import { NotificationService } from '../../core/services/notification.service';
import { AuthService } from '../../core/services/auth.service';
import { HardwareDetectorService } from '../../core/services/hardware-detector.service';
import { LlmProvider } from '../../shared/models/mod.model';
import { detectProvider } from '../../core/utils/key-detection';
import { ApiKeyGuideComponent } from '../../shared/components/api-key-guide/api-key-guide.component';

type SettingsTab = 'profile' | 'hardware' | 'notifications';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [FormsModule, ApiKeyGuideComponent],
  animations: [
    trigger('fadeIn', [
      transition(':enter', [
        style({ opacity: 0 }),
        animate('250ms ease-out', style({ opacity: 1 })),
      ]),
    ]),
  ],
  template: `
    <div class="settings-page">
      <div class="settings-header">
        <h1>Settings</h1>
        <p>Manage your profile, hardware, and preferences</p>
      </div>

      <!-- Tabs -->
      <div class="tabs">
        @for (tab of tabs; track tab.id) {
          <button
            class="tab"
            [class.active]="activeTab() === tab.id"
            (click)="activeTab.set(tab.id)"
          >
            {{ tab.label }}
          </button>
        }
      </div>

      <!-- Tab Content -->
      <div class="tab-content">
        @switch (activeTab()) {
          @case ('profile') {
            <div class="tab-panel" @fadeIn>
              <div class="panel-section">
                <h3>Display Name</h3>
                <input type="text" class="input" [(ngModel)]="displayName" placeholder="Your display name">
              </div>
              <div class="panel-section">
                <h3>Email</h3>
                <input type="email" class="input" [value]="email" disabled>
                <p class="input-hint">Email cannot be changed.</p>
              </div>
              @if (!emailVerified) {
                <div class="panel-section verify-banner">
                  <div class="verify-info">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10"/>
                      <line x1="12" y1="8" x2="12" y2="12"/>
                      <line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                    <span>Email not verified.</span>
                  </div>
                  <button class="btn-verify" (click)="resendVerification()">Resend Link</button>
                </div>
              }
              <div class="panel-section">
                <h3>Connected Accounts</h3>
                <p class="input-hint" style="margin-bottom: 0.75rem;">Link additional sign-in methods to your account.</p>
                <div class="connected-list">
                  @for (p of availableProviders; track p.id) {
                    <div class="connected-item">
                      <div class="connected-info">
                        <span class="provider-name">{{ p.label }}</span>
                        @if (isProviderConnected(p.id)) {
                          <span class="connected-badge">Connected</span>
                        }
                      </div>
                      @if (isProviderConnected(p.id)) {
                        <button
                          class="btn-disconnect"
                          (click)="disconnectProvider(p.id)"
                          [disabled]="!canDisconnect()"
                          [title]="canDisconnect() ? 'Disconnect ' + p.label : 'Set a password before disconnecting your only sign-in method'"
                        >
                          Disconnect
                        </button>
                      } @else {
                        <button class="btn-connect" (click)="connectProvider(p.id)">
                          Connect
                        </button>
                      }
                    </div>
                  }
                </div>
              </div>
              <div class="panel-section">
                <h3>Nexus Mods API Key</h3>
                <input type="password" class="input" [(ngModel)]="nexusApiKey" placeholder="Enter your Nexus Mods API key">
                <p class="input-hint">Required for mod downloads. Get your key from Nexus Mods account settings.</p>
              </div>
              <div class="panel-section">
                <h3>AI Provider API Keys</h3>
                <div class="key-security-notice">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                  </svg>
                  <span>Your API keys are stored securely and only used during modlist generation. Never share your keys with anyone.</span>
                </div>
                <p class="input-hint" style="margin-bottom: 0.75rem;">
                  Paste an API key below — the provider will be detected automatically.
                  If one provider hits a rate limit during generation, the next is used.
                </p>

                <app-api-key-guide [providers]="llmProviders()" />

                <!-- Add Key Input -->
                <div class="add-key-row">
                  <div class="key-input-wrap">
                    <input
                      type="password"
                      [value]="newKeyInput()"
                      (input)="newKeyInput.set($any($event.target).value)"
                      (paste)="onKeyPaste($event)"
                      placeholder="Paste any AI provider API key..."
                      autocomplete="off"
                      spellcheck="false"
                    />
                  </div>
                  <button class="btn-add-key" (click)="addKey()" [disabled]="!newKeyInput()">
                    Add Key
                  </button>
                </div>

                <!-- Detection feedback -->
                @if (detectionState()) {
                  <div class="detection-feedback" [class.warning]="detectionState()!.type !== 'exact'" @fadeIn>
                    @if (detectionState()!.type === 'exact') {
                      <div class="detection-exact">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                          <polyline points="20 6 9 17 4 12"/>
                        </svg>
                        Detected: <strong>{{ detectionState()!.providerName }}</strong>
                      </div>
                    } @else if (detectionState()!.type === 'ambiguous') {
                      <div class="detection-warn">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <circle cx="12" cy="12" r="10"/>
                          <line x1="12" y1="8" x2="12" y2="12"/>
                          <line x1="12" y1="16" x2="12.01" y2="16"/>
                        </svg>
                        <span>This key prefix matches multiple providers. Please select the correct one:</span>
                      </div>
                      <select class="input detection-select" (change)="confirmProvider($any($event.target).value)">
                        <option value="" disabled selected>Select provider...</option>
                        @for (m of detectionState()!.matches; track m.id) {
                          <option [value]="m.id">{{ m.name }}</option>
                        }
                      </select>
                    } @else {
                      <div class="detection-warn">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <circle cx="12" cy="12" r="10"/>
                          <line x1="12" y1="8" x2="12" y2="12"/>
                          <line x1="12" y1="16" x2="12.01" y2="16"/>
                        </svg>
                        <span>Could not identify the provider from this key. Please select it manually:</span>
                      </div>
                      <select class="input detection-select" (change)="confirmProvider($any($event.target).value)">
                        <option value="" disabled selected>Select provider...</option>
                        @for (p of llmProviders(); track p.id) {
                          <option [value]="p.id">{{ p.name }}</option>
                        }
                      </select>
                    }
                  </div>
                }

                <!-- Saved Keys List -->
                @if (savedKeysList().length > 0) {
                  <div class="saved-keys">
                    @for (entry of savedKeysList(); track entry.providerId) {
                      <div class="saved-key-row">
                        <div class="saved-key-info">
                          <span class="saved-key-provider">{{ entry.providerName }}</span>
                          <span class="saved-key-masked">{{ entry.maskedKey }}</span>
                        </div>
                        <div class="saved-key-actions">
                          @if (editingKeyProvider() === entry.providerId) {
                            <select class="input reassign-select" (change)="reassignKey(entry.providerId, $any($event.target).value)">
                              <option value="" disabled selected>Move to...</option>
                              @for (p of llmProviders(); track p.id) {
                                @if (p.id !== entry.providerId) {
                                  <option [value]="p.id">{{ p.name }}</option>
                                }
                              }
                            </select>
                            <button class="btn-icon" (click)="editingKeyProvider.set(null)" title="Cancel">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                              </svg>
                            </button>
                          } @else {
                            <button class="btn-icon" (click)="editingKeyProvider.set(entry.providerId)" title="Reassign to different provider">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                              </svg>
                            </button>
                            <button class="btn-icon btn-delete" (click)="deleteKey(entry.providerId)" title="Remove key">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"/>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                              </svg>
                            </button>
                          }
                        </div>
                      </div>
                    }
                  </div>
                }
              </div>
            </div>
          }
          @case ('hardware') {
            <div class="tab-panel" @fadeIn>
              <!-- Auto-Detect Section -->
              <div class="panel-section">
                <h3>Auto-Detect</h3>
                <p class="input-hint" style="margin-bottom: 0.75rem;">Detect your GPU automatically via your browser. VRAM is inferred from the GPU model.</p>
                <button class="btn-scan btn-detect" (click)="autoDetect()" [disabled]="scanLoading()">
                  @if (scanLoading() && !hardwareRawText.trim()) {
                    <span class="btn-spinner"></span>
                    Detecting...
                  } @else {
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="3"/>
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                    </svg>
                    Auto-Detect Hardware
                  }
                </button>
              </div>

              <!-- Paste & Scan Section -->
              <div class="panel-section">
                <div class="section-header-row">
                  <h3>Paste & Scan</h3>
                  <button class="btn-toggle-help" (click)="showHelpGuide.set(!showHelpGuide())">
                    {{ showHelpGuide() ? 'Hide guide' : 'How to find your specs' }}
                  </button>
                </div>
                @if (showHelpGuide()) {
                  <div class="help-guide" @fadeIn>
                    <div class="help-option">
                      <h4>Option 1: PowerShell Command</h4>
                      <p>Open PowerShell and run this command, then paste the output below:</p>
                      <div class="code-block">
                        <code>{{ powershellCommand }}</code>
                        <button class="btn-copy" (click)="copyCommand()" [title]="'Copy to clipboard'">
                          {{ commandCopied() ? 'Copied!' : 'Copy' }}
                        </button>
                      </div>
                    </div>
                    <div class="help-option">
                      <h4>Option 2: Task Manager</h4>
                      <p>Open Task Manager (Ctrl+Shift+Esc) &rarr; Performance tab &rarr; note your CPU name, GPU name, and memory values. Paste or type them below.</p>
                    </div>
                    <div class="help-option">
                      <h4>Option 3: NVIDIA App / AMD Software</h4>
                      <p>Open your GPU software &rarr; System Information &rarr; copy the hardware details and paste below.</p>
                    </div>
                  </div>
                }
                <textarea
                  class="input scan-textarea"
                  [(ngModel)]="hardwareRawText"
                  placeholder="Paste hardware info from PowerShell output, NVIDIA App, HWiNFO, or Task Manager..."
                  rows="4"
                ></textarea>
                <button class="btn-scan" (click)="scanHardware()" [disabled]="scanLoading() || !hardwareRawText.trim()">
                  @if (scanLoading() && hardwareRawText.trim()) {
                    <span class="btn-spinner"></span>
                    Scanning...
                  } @else {
                    Scan & Fill
                  }
                </button>
              </div>

              <!-- Hardware Fields -->
              <div class="panel-section">
                <h3>GPU Model</h3>
                <input type="text" class="input" [(ngModel)]="gpuModel" placeholder="e.g. NVIDIA GeForce RTX 4070">
              </div>
              <div class="panel-section">
                <h3>VRAM</h3>
                <div class="slider-group">
                  <input type="range" class="slider" min="2" max="24" step="1" [(ngModel)]="vramGb">
                  <span class="slider-value">{{ vramGb }} GB</span>
                </div>
              </div>
              <div class="panel-section">
                <h3>System RAM</h3>
                <div class="slider-group">
                  <input type="range" class="slider" min="4" max="64" step="4" [(ngModel)]="ramGb">
                  <span class="slider-value">{{ ramGb }} GB</span>
                </div>
              </div>
              <div class="panel-section">
                <h3>CPU Model</h3>
                <input type="text" class="input" [(ngModel)]="cpuModel" placeholder="e.g. AMD Ryzen 7 7800X3D">
              </div>
              @if (storageDrives) {
                <div class="panel-section">
                  <h3>Storage Drives</h3>
                  <div class="drives-list">
                    @for (drive of parsedDrives(); track drive.letter) {
                      <div class="drive-item">
                        <span class="drive-letter">{{ drive.letter }}</span>
                        <div class="drive-bar-container">
                          <div class="drive-bar" [style.width.%]="drive.usedPct"></div>
                        </div>
                        <span class="drive-info">{{ drive.freeGb }} GB free / {{ drive.totalGb }} GB</span>
                      </div>
                    }
                  </div>
                </div>
              }
              <div class="hw-summary">
                <h4>Hardware Summary</h4>
                <div class="hw-grid">
                  <div class="hw-item">
                    <span class="hw-label">GPU</span>
                    <span class="hw-val">{{ gpuModel || 'Not set' }}</span>
                  </div>
                  <div class="hw-item">
                    <span class="hw-label">VRAM</span>
                    <span class="hw-val">{{ vramGb }} GB</span>
                  </div>
                  <div class="hw-item">
                    <span class="hw-label">RAM</span>
                    <span class="hw-val">{{ ramGb }} GB</span>
                  </div>
                  <div class="hw-item">
                    <span class="hw-label">CPU</span>
                    <span class="hw-val">{{ cpuModel || 'Not set' }}</span>
                  </div>
                  @if (storageDrives) {
                    <div class="hw-item" style="grid-column: 1 / -1;">
                      <span class="hw-label">Storage</span>
                      <span class="hw-val">{{ storageDrives }}</span>
                    </div>
                  }
                </div>
              </div>
            </div>
          }
          @case ('notifications') {
            <div class="tab-panel" @fadeIn>
              <div class="notif-item">
                <div class="notif-info">
                  <h3>Email Alerts</h3>
                  <p>Get notified about important updates and new features.</p>
                </div>
                <button class="toggle-switch" [class.on]="emailAlerts" (click)="emailAlerts = !emailAlerts">
                  <span class="toggle-knob"></span>
                </button>
              </div>
              <div class="notif-item">
                <div class="notif-info">
                  <h3>New Mod Recommendations</h3>
                  <p>Receive suggestions when new mods match your preferences.</p>
                </div>
                <button class="toggle-switch" [class.on]="modRecommendations" (click)="modRecommendations = !modRecommendations">
                  <span class="toggle-knob"></span>
                </button>
              </div>
              <div class="notif-item">
                <div class="notif-info">
                  <h3>Compatibility Warnings</h3>
                  <p>Get alerts when mod updates may cause conflicts.</p>
                </div>
                <button class="toggle-switch" [class.on]="compatWarnings" (click)="compatWarnings = !compatWarnings">
                  <span class="toggle-knob"></span>
                </button>
              </div>
            </div>
          }
        }
      </div>

      <!-- Save Button -->
      <div class="save-bar">
        <button class="btn-save" (click)="saveSettings()">
          Save Changes
        </button>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }

    .settings-page {
      max-width: 680px;
      margin: 0 auto;
      padding: 2rem;
    }
    .settings-header {
      margin-bottom: 2rem;
    }
    .settings-header h1 {
      font-size: 1.5rem;
      font-weight: 600;
      letter-spacing: -0.01em;
    }
    .settings-header p {
      font-size: 0.875rem;
      color: var(--color-text-muted);
      margin-top: 0.25rem;
    }

    /* Tabs */
    .tabs {
      display: flex;
      gap: 0.25rem;
      border-bottom: 1px solid var(--color-border);
      margin-bottom: 2rem;
    }
    .tab {
      padding: 0.625rem 1rem;
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--color-text-muted);
      background: none;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
      transition: color 0.15s, border-color 0.15s;
    }
    .tab:hover { color: var(--color-text); }
    .tab.active {
      color: var(--color-text);
      border-bottom-color: var(--color-gold);
    }

    /* Panel */
    .tab-panel {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }
    .panel-section {
      padding: 1rem 0;
      border-bottom: 1px solid var(--color-border);
    }
    .panel-section.sub {
      padding-left: 1rem;
      border-left: 2px solid var(--color-border);
      margin-left: 0.5rem;
    }
    .panel-section:last-child { border-bottom: none; }
    .panel-section h3 {
      font-size: 0.875rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
    }

    /* Inputs */
    .input {
      width: 100%;
      background: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: 8px;
      color: var(--color-text);
      padding: 0.625rem 0.875rem;
      font-size: 0.875rem;
      outline: none;
      transition: border-color 0.15s;
    }
    .input:focus { border-color: var(--color-gold); }
    select.input { cursor: pointer; }
    .input::placeholder { color: var(--color-text-dim); }
    .input-hint {
      font-size: 0.75rem;
      color: var(--color-text-dim);
      margin-top: 0.375rem;
    }

    /* Slider */
    .slider-group {
      display: flex;
      align-items: center;
      gap: 1rem;
    }
    .slider {
      flex: 1;
      -webkit-appearance: none;
      appearance: none;
      height: 4px;
      background: var(--color-border);
      border-radius: 2px;
      outline: none;
    }
    .slider::-webkit-slider-thumb {
      -webkit-appearance: none;
      appearance: none;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: var(--color-gold);
      cursor: pointer;
      border: 3px solid var(--color-bg-dark);
      box-shadow: 0 0 0 1px var(--color-gold);
    }
    .slider::-moz-range-thumb {
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: var(--color-gold);
      cursor: pointer;
      border: 3px solid var(--color-bg-dark);
    }
    .slider-value {
      font-size: 0.875rem;
      font-weight: 600;
      min-width: 50px;
      text-align: right;
    }

    /* Hardware summary */
    .hw-summary {
      margin-top: 1.5rem;
      background: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: 10px;
      padding: 1.25rem;
    }
    .hw-summary h4 {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--color-text-muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 1rem;
    }
    .hw-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
    }
    .hw-item {
      display: flex;
      flex-direction: column;
      gap: 0.125rem;
    }
    .hw-label {
      font-size: 0.75rem;
      color: var(--color-text-dim);
    }
    .hw-val {
      font-size: 0.875rem;
      font-weight: 500;
    }
    .capitalize { text-transform: capitalize; }

    /* Verify Banner */
    .verify-banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: rgba(234, 179, 8, 0.08);
      border: 1px solid rgba(234, 179, 8, 0.2) !important;
      border-radius: 8px;
      padding: 0.75rem 1rem !important;
    }
    .verify-info {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      color: var(--color-warning);
      font-size: 0.8125rem;
      font-weight: 500;
    }
    .btn-verify {
      background: var(--color-gold);
      color: #0D0D0F;
      padding: 0.375rem 0.875rem;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
      transition: background 0.2s;
    }
    .btn-verify:hover { background: var(--color-gold-hover); }

    /* Connected Accounts */
    .connected-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .connected-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.625rem 0.875rem;
      background: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: 8px;
    }
    .connected-info {
      display: flex;
      align-items: center;
      gap: 0.625rem;
    }
    .provider-name {
      font-size: 0.875rem;
      font-weight: 500;
    }
    .connected-badge {
      font-size: 0.6875rem;
      font-weight: 600;
      color: #22c55e;
      background: rgba(34, 197, 94, 0.1);
      border: 1px solid rgba(34, 197, 94, 0.25);
      padding: 0.125rem 0.5rem;
      border-radius: 100px;
    }
    .btn-connect {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--color-border);
      color: var(--color-text);
      padding: 0.375rem 0.875rem;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
      transition: border-color 0.15s, background 0.15s;
    }
    .btn-connect:hover {
      border-color: var(--color-gold);
      background: rgba(192, 160, 96, 0.08);
      color: var(--color-gold);
    }
    .btn-disconnect {
      background: transparent;
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #ef4444;
      padding: 0.375rem 0.875rem;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
      transition: background 0.15s, border-color 0.15s;
    }
    .btn-disconnect:hover:not(:disabled) {
      background: rgba(239, 68, 68, 0.08);
      border-color: #ef4444;
    }
    .btn-disconnect:disabled { opacity: 0.35; cursor: not-allowed; }

    /* Storage Drives */
    .drives-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .drive-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .drive-letter {
      font-size: 0.8125rem;
      font-weight: 600;
      min-width: 24px;
      color: var(--color-gold);
    }
    .drive-bar-container {
      flex: 1;
      height: 6px;
      background: var(--color-border);
      border-radius: 3px;
      overflow: hidden;
    }
    .drive-bar {
      height: 100%;
      background: var(--color-gold);
      border-radius: 3px;
      transition: width 0.3s ease;
    }
    .drive-info {
      font-size: 0.75rem;
      color: var(--color-text-muted);
      min-width: 140px;
      text-align: right;
    }

    /* Scan */
    .scan-textarea {
      resize: vertical;
      min-height: 80px;
      font-family: 'Fira Code', 'Consolas', monospace;
      font-size: 0.8125rem;
      line-height: 1.5;
    }
    .btn-scan {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      margin-top: 0.5rem;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--color-border);
      color: var(--color-text);
      padding: 0.5rem 1rem;
      border-radius: 8px;
      font-size: 0.8125rem;
      font-weight: 500;
      transition: border-color 0.15s, background 0.15s;
    }
    .btn-scan:hover:not(:disabled) {
      border-color: var(--color-border-hover);
      background: rgba(255, 255, 255, 0.08);
    }
    .btn-scan:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-detect {
      background: rgba(192, 160, 96, 0.08);
      border-color: rgba(192, 160, 96, 0.3);
      color: var(--color-gold);
      margin-top: 0;
    }
    .btn-detect:hover:not(:disabled) {
      background: rgba(192, 160, 96, 0.15);
      border-color: var(--color-gold);
    }
    .btn-spinner {
      width: 12px;
      height: 12px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: var(--color-text);
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* Section header with toggle */
    .section-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.5rem;
    }
    .section-header-row h3 { margin-bottom: 0; }
    .btn-toggle-help {
      background: none;
      border: none;
      color: var(--color-text-muted);
      font-size: 0.75rem;
      font-weight: 500;
      padding: 0;
      cursor: pointer;
      text-decoration: underline;
      text-underline-offset: 2px;
    }
    .btn-toggle-help:hover { color: var(--color-text); }

    /* Help guide */
    .help-guide {
      background: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: 10px;
      padding: 1rem;
      margin-bottom: 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .help-option h4 {
      font-size: 0.8125rem;
      font-weight: 600;
      margin-bottom: 0.25rem;
      color: var(--color-gold);
    }
    .help-option p {
      font-size: 0.8125rem;
      color: var(--color-text-muted);
      line-height: 1.4;
    }
    .code-block {
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
      margin-top: 0.5rem;
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid var(--color-border);
      border-radius: 8px;
      padding: 0.75rem;
    }
    .code-block code {
      flex: 1;
      font-family: 'Fira Code', 'Consolas', monospace;
      font-size: 0.75rem;
      line-height: 1.5;
      color: var(--color-text-muted);
      word-break: break-all;
      white-space: pre-wrap;
    }
    .btn-copy {
      flex-shrink: 0;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--color-border);
      color: var(--color-text-muted);
      padding: 0.25rem 0.625rem;
      border-radius: 6px;
      font-size: 0.6875rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }
    .btn-copy:hover {
      border-color: var(--color-gold);
      color: var(--color-gold);
    }

    /* Security notice */
    .key-security-notice {
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
      padding: 0.625rem 0.75rem;
      background: rgba(192, 160, 96, 0.06);
      border: 1px solid rgba(192, 160, 96, 0.15);
      border-radius: 8px;
      margin-bottom: 0.75rem;
      font-size: 0.75rem;
      color: var(--color-text-muted);
      line-height: 1.4;
    }
    .key-security-notice svg {
      flex-shrink: 0;
      margin-top: 1px;
      color: var(--color-gold);
    }

    /* Add key row */
    .add-key-row {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 0.5rem;
    }
    .add-key-row .key-input-wrap {
      flex: 1;
      display: flex;
      align-items: center;
      background: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: 8px;
      overflow: hidden;
      transition: border-color 0.15s;
    }
    .add-key-row .key-input-wrap:focus-within {
      border-color: var(--color-gold);
    }
    .add-key-row .key-input-wrap input {
      flex: 1;
      background: none;
      border: none;
      color: var(--color-text);
      font-size: 0.8125rem;
      padding: 0.625rem 0.875rem;
      outline: none;
      font-family: monospace;
      min-width: 0;
    }
    .add-key-row .key-input-wrap input::placeholder {
      color: var(--color-text-dim);
      font-family: inherit;
    }
    .btn-add-key {
      background: var(--color-gold);
      color: #0D0D0F;
      padding: 0.5rem 1rem;
      border-radius: 8px;
      font-size: 0.8125rem;
      font-weight: 600;
      white-space: nowrap;
      transition: background 0.2s;
    }
    .btn-add-key:hover:not(:disabled) { background: var(--color-gold-hover); }
    .btn-add-key:disabled { opacity: 0.4; cursor: not-allowed; }

    /* Detection feedback */
    .detection-feedback {
      padding: 0.625rem 0.75rem;
      border-radius: 8px;
      margin-bottom: 0.75rem;
      font-size: 0.8125rem;
    }
    .detection-feedback:not(.warning) {
      background: rgba(34, 197, 94, 0.08);
      border: 1px solid rgba(34, 197, 94, 0.2);
    }
    .detection-feedback.warning {
      background: rgba(234, 179, 8, 0.08);
      border: 1px solid rgba(234, 179, 8, 0.2);
    }
    .detection-exact {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      color: #22c55e;
      font-weight: 500;
    }
    .detection-exact strong { color: var(--color-text); }
    .detection-warn {
      display: flex;
      align-items: flex-start;
      gap: 0.375rem;
      color: var(--color-warning);
      margin-bottom: 0.5rem;
    }
    .detection-warn svg { flex-shrink: 0; margin-top: 2px; }
    .detection-select {
      margin-top: 0.25rem;
      font-size: 0.8125rem;
    }

    /* Saved keys list */
    .saved-keys {
      display: flex;
      flex-direction: column;
      gap: 0.375rem;
      margin-top: 0.5rem;
    }
    .saved-key-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.625rem 0.75rem;
      background: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: 8px;
    }
    .saved-key-info {
      display: flex;
      align-items: center;
      gap: 0.625rem;
      min-width: 0;
    }
    .saved-key-provider {
      font-size: 0.8125rem;
      font-weight: 600;
      white-space: nowrap;
    }
    .saved-key-masked {
      font-size: 0.75rem;
      color: var(--color-text-dim);
      font-family: monospace;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .saved-key-actions {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      flex-shrink: 0;
    }
    .btn-icon {
      background: none;
      border: none;
      color: var(--color-text-muted);
      padding: 0.375rem;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      transition: color 0.15s, background 0.15s;
    }
    .btn-icon:hover { color: var(--color-text); background: rgba(255,255,255,0.06); }
    .btn-delete:hover { color: #ef4444; background: rgba(239,68,68,0.08); }
    .reassign-select {
      font-size: 0.75rem;
      padding: 0.25rem 0.5rem;
      max-width: 140px;
    }

    /* Notification items */
    .notif-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1.25rem 0;
      border-bottom: 1px solid var(--color-border);
    }
    .notif-item:last-child { border-bottom: none; }
    .notif-info h3 {
      font-size: 0.875rem;
      font-weight: 600;
      margin-bottom: 0.125rem;
    }
    .notif-info p {
      font-size: 0.8125rem;
      color: var(--color-text-muted);
    }
    .toggle-switch {
      width: 44px;
      height: 24px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.1);
      position: relative;
      flex-shrink: 0;
      transition: background 0.2s;
      padding: 0;
    }
    .toggle-switch.on { background: var(--color-gold); }
    .toggle-knob {
      position: absolute;
      top: 2px;
      left: 2px;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: white;
      transition: transform 0.2s;
    }
    .toggle-switch.on .toggle-knob {
      transform: translateX(20px);
    }

    /* Save */
    .save-bar {
      margin-top: 2rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--color-border);
    }
    .btn-save {
      background: var(--color-gold);
      color: #0D0D0F;
      padding: 0.625rem 2rem;
      border-radius: 8px;
      font-size: 0.875rem;
      font-weight: 600;
      transition: background 0.2s, box-shadow 0.3s;
    }
    .btn-save:hover {
      background: var(--color-gold-hover);
      box-shadow: 0 0 20px var(--color-gold-glow);
    }
  `],
})
export class SettingsComponent implements OnInit {
  activeTab = signal<SettingsTab>('profile');

  tabs: { id: SettingsTab; label: string }[] = [
    { id: 'profile', label: 'Profile' },
    { id: 'hardware', label: 'Hardware' },
    { id: 'notifications', label: 'Notifications' },
  ];

  // Profile
  displayName = '';
  email = '';
  emailVerified = false;
  hasPassword = false;
  connectedProviders = signal<string[]>([]);
  availableProviders = [
    { id: 'google' as const, label: 'Google' },
    { id: 'discord' as const, label: 'Discord' },
  ];
  nexusApiKey = '';

  // LLM Providers (registry-based)
  llmProviders = signal<LlmProvider[]>([]);
  llmKeys = signal<Record<string, string>>({});

  // Dynamic key entry state
  newKeyInput = signal('');
  detectionState = signal<{
    type: 'exact' | 'ambiguous' | 'unknown';
    providerId?: string;
    providerName?: string;
    matches?: { id: string; name: string }[];
  } | null>(null);
  editingKeyProvider = signal<string | null>(null);
  savedKeysList = computed(() => {
    const keys = this.llmKeys();
    const providers = this.llmProviders();
    return Object.entries(keys)
      .filter(([, key]) => key.length > 0)
      .map(([providerId, key]) => {
        const provider = providers.find(p => p.id === providerId);
        const masked = key.length > 12
          ? key.substring(0, 6) + '...' + key.substring(key.length - 4)
          : '***';
        return {
          providerId,
          providerName: provider?.name || providerId,
          maskedKey: masked,
        };
      });
  });

  // Hardware
  gpuModel = '';
  vramGb = 8;
  ramGb = 16;
  cpuModel = '';
  hardwareTier = '';
  hardwareRawText = '';
  storageDrives = '';
  storageDrivesSignal = signal('');
  parsedDrives = computed(() => {
    const raw = this.storageDrivesSignal();
    if (!raw) return [];
    return raw.split(',').map(part => {
      const m = part.trim().match(/^([A-Z]:)\s*(\d+)\s*GB\s*free\s*\/\s*(\d+)\s*GB$/i);
      if (!m) return null;
      const freeGb = parseInt(m[2]);
      const totalGb = parseInt(m[3]);
      const usedPct = totalGb > 0 ? Math.round(((totalGb - freeGb) / totalGb) * 100) : 0;
      return { letter: m[1], freeGb, totalGb, usedPct };
    }).filter((d): d is NonNullable<typeof d> => d !== null);
  });
  scanLoading = signal(false);
  showHelpGuide = signal(false);
  commandCopied = signal(false);
  powershellCommand = `$gpu=Get-CimInstance Win32_VideoController|Sort-Object AdapterRAM -Descending|Select -First 1;$g=$gpu.Name;try{$v=[math]::Round((nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>$null|Select -First 1)/1024)}catch{$v=0};if(!$v){$v=[math]::Round($gpu.AdapterRAM/1GB)};$c=(Get-CimInstance Win32_Processor).Name;$r=[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB);$n=(Get-CimInstance Win32_Processor).NumberOfCores;$t=(Get-CimInstance Win32_Processor).NumberOfLogicalProcessors;$d=(Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3"|ForEach-Object{"$($_.DeviceID) $([math]::Round($_.FreeSpace/1GB))GB free / $([math]::Round($_.Size/1GB))GB"}) -join ", ";"GPU: $g\`nVRAM: $v GB\`nCPU: $c\`nCores: $n cores / $t threads\`nRAM: $r GB\`nDrives: $d"`;

  // Notifications
  emailAlerts = true;
  modRecommendations = true;
  compatWarnings = true;

  constructor(
    private api: ApiService,
    private notifications: NotificationService,
    private authService: AuthService,
    private hardwareDetector: HardwareDetectorService,
  ) {}

  ngOnInit(): void {
    this.loadProfile();
    this.loadSettings();
    this.loadHardware();
    this.loadConnectedAccounts();
    this.loadLlmProviders();
    this.loadLlmKeys();
  }

  onKeyPaste(event: ClipboardEvent): void {
    const pasted = event.clipboardData?.getData('text')?.trim();
    if (!pasted) return;
    // Let the input update first, then run detection
    setTimeout(() => this.runDetection(pasted), 0);
  }

  addKey(): void {
    const key = this.newKeyInput().trim();
    if (!key) return;

    const state = this.detectionState();
    if (state?.type === 'exact' && state.providerId) {
      this.saveDetectedKey(state.providerId, key);
    } else if (!state) {
      // Run detection if not yet run (user typed instead of pasting)
      this.runDetection(key);
    }
    // For ambiguous/unknown, user must pick from dropdown first (confirmProvider)
  }

  confirmProvider(providerId: string): void {
    if (!providerId) return;
    const key = this.newKeyInput().trim();
    if (!key) return;
    this.saveDetectedKey(providerId, key);
  }

  deleteKey(providerId: string): void {
    this.llmKeys.update(keys => {
      const updated = { ...keys };
      delete updated[providerId];
      return updated;
    });
    // Persist deletion to backend
    this.api.saveLlmKeys({ [providerId]: '' }).subscribe({
      error: () => this.notifications.error('Failed to remove key'),
    });
    this.notifications.success('API key removed');
  }

  reassignKey(oldProviderId: string, newProviderId: string): void {
    if (!newProviderId) return;
    const keys = this.llmKeys();
    const key = keys[oldProviderId];
    if (!key) return;

    // Remove old, add new
    this.llmKeys.update(k => {
      const updated = { ...k };
      delete updated[oldProviderId];
      updated[newProviderId] = key;
      return updated;
    });

    // Persist both changes
    this.api.saveLlmKeys({ [oldProviderId]: '', [newProviderId]: key }).subscribe({
      error: () => this.notifications.error('Failed to reassign key'),
    });

    this.editingKeyProvider.set(null);
    const provider = this.llmProviders().find(p => p.id === newProviderId);
    this.notifications.success(`Key reassigned to ${provider?.name || newProviderId}`);
  }

  private runDetection(key: string): void {
    const result = detectProvider(key, this.llmProviders());

    if (!result) {
      this.detectionState.set({ type: 'unknown' });
      return;
    }

    if (result.confidence === 'exact') {
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

  private saveDetectedKey(providerId: string, key: string): void {
    this.llmKeys.update(keys => ({ ...keys, [providerId]: key }));
    this.api.saveLlmKeys({ [providerId]: key }).subscribe({
      error: () => this.notifications.error('Failed to save key'),
    });

    const provider = this.llmProviders().find(p => p.id === providerId);
    this.notifications.success(`${provider?.name || providerId} key saved`);

    // Reset input state
    this.newKeyInput.set('');
    this.detectionState.set(null);
  }

  resendVerification(): void {
    this.authService.resendVerification().subscribe({
      next: () => this.notifications.success('Verification email sent'),
      error: () => this.notifications.error('Failed to send verification email'),
    });
  }

  async autoDetect(): Promise<void> {
    this.scanLoading.set(true);
    try {
      const detected = await this.hardwareDetector.detect();
      if (!detected.formatted) {
        this.scanLoading.set(false);
        this.notifications.error('Could not detect hardware. Try pasting your specs manually.');
        return;
      }
      this.hardwareRawText = detected.formatted;
      // Send detected text to backend for parsing + tier classification
      this.api.parseSpecs(detected.formatted).subscribe({
        next: (response) => {
          this.scanLoading.set(false);
          this.applyParsedSpecs(response);
          this.notifications.success('Hardware detected successfully');
        },
        error: () => {
          this.scanLoading.set(false);
          this.notifications.error('Hardware detected but failed to classify. You can adjust fields manually.');
        },
      });
    } catch {
      this.scanLoading.set(false);
      this.notifications.error('Could not detect hardware. Try pasting your specs manually.');
    }
  }

  copyCommand(): void {
    navigator.clipboard.writeText(this.powershellCommand).then(() => {
      this.commandCopied.set(true);
      setTimeout(() => this.commandCopied.set(false), 2000);
    });
  }

  scanHardware(): void {
    if (!this.hardwareRawText.trim()) return;
    this.scanLoading.set(true);
    this.api.parseSpecs(this.hardwareRawText).subscribe({
      next: (response) => {
        this.scanLoading.set(false);
        this.applyParsedSpecs(response);
        this.notifications.success('Hardware info scanned successfully');
      },
      error: () => {
        this.scanLoading.set(false);
        this.notifications.error('Failed to scan hardware info');
      },
    });
  }

  private applyParsedSpecs(response: any): void {
    if (response.specs) {
      if (response.specs.gpu) this.gpuModel = response.specs.gpu;
      if (response.specs.cpu) this.cpuModel = response.specs.cpu;
      if (response.specs.ram_gb) this.ramGb = response.specs.ram_gb;
      if (response.specs.vram_mb) this.vramGb = Math.round(response.specs.vram_mb / 1024);
      if (response.specs.storage_drives) {
        this.storageDrives = response.specs.storage_drives;
        this.storageDrivesSignal.set(response.specs.storage_drives);
      }
    }
    if (response.tier) this.hardwareTier = response.tier;
  }

  private loadProfile(): void {
    const user = this.authService.user();
    if (user) {
      this.displayName = user.display_name || '';
      this.email = user.email;
      this.emailVerified = user.email_verified;
      this.hasPassword = user.auth_provider === 'local';
    }
  }

  private loadHardware(): void {
    this.authService.getHardware().subscribe({
      next: (hw) => {
        if (hw) {
          this.gpuModel = hw.gpu_model || '';
          this.cpuModel = hw.cpu_model || '';
          this.ramGb = hw.ram_gb || 16;
          this.vramGb = hw.vram_mb ? Math.round(hw.vram_mb / 1024) : 8;
          this.hardwareTier = hw.hardware_tier || '';
          this.hardwareRawText = hw.hardware_raw_text || '';
          this.storageDrives = hw.storage_drives || '';
          this.storageDrivesSignal.set(hw.storage_drives || '');
        }
      },
      error: () => {},
    });
  }

  private loadSettings(): void {
    this.api.getSettings().subscribe({
      next: (settings: any) => {
        this.nexusApiKey = settings.nexus_api_key || '';
        this.emailAlerts = settings.email_alerts ?? true;
        this.modRecommendations = settings.mod_recommendations ?? true;
        this.compatWarnings = settings.compat_warnings ?? true;
      },
      error: () => {},
    });
  }

  private loadLlmProviders(): void {
    this.api.getLlmProviders().subscribe({
      next: (providers) => this.llmProviders.set(providers),
      error: () => {},
    });
  }

  private loadLlmKeys(): void {
    this.api.getLlmKeys().subscribe({
      next: (keys) => this.llmKeys.set(keys),
      error: () => {},
    });
  }

  private loadConnectedAccounts(): void {
    this.authService.getConnectedAccounts().subscribe({
      next: (accounts) => {
        this.connectedProviders.set(accounts.map((a) => a.provider));
      },
      error: () => {},
    });
  }

  isProviderConnected(providerId: string): boolean {
    return this.connectedProviders().includes(providerId);
  }

  canDisconnect(): boolean {
    return this.hasPassword || this.connectedProviders().length > 1;
  }

  connectProvider(providerId: 'google' | 'discord'): void {
    this.authService.oauthLogin(providerId);
  }

  disconnectProvider(providerId: string): void {
    this.authService.disconnectAccount(providerId).subscribe({
      next: () => {
        this.connectedProviders.update((providers) =>
          providers.filter((p) => p !== providerId),
        );
        this.notifications.success(`${providerId.charAt(0).toUpperCase() + providerId.slice(1)} disconnected`);
      },
      error: () => {
        this.notifications.error('Failed to disconnect account');
      },
    });
  }

  saveSettings(): void {
    // Save profile
    this.authService.updateProfile({ display_name: this.displayName }).subscribe({
      error: () => this.notifications.error('Failed to save profile'),
    });

    // Save hardware
    this.authService.saveHardware({
      gpu_model: this.gpuModel || undefined,
      cpu_model: this.cpuModel || undefined,
      ram_gb: this.ramGb,
      vram_mb: this.vramGb * 1024,
      hardware_raw_text: this.hardwareRawText || undefined,
      storage_drives: this.storageDrives || undefined,
    }).subscribe({
      next: (hw) => {
        this.hardwareTier = hw.hardware_tier || '';
      },
      error: () => this.notifications.error('Failed to save hardware'),
    });

    // Save settings (Nexus key + notification prefs)
    this.api.updateSettings({
      nexus_api_key: this.nexusApiKey,
      email_alerts: this.emailAlerts,
      mod_recommendations: this.modRecommendations,
      compat_warnings: this.compatWarnings,
    }).subscribe({
      error: () => this.notifications.error('Failed to save settings'),
    });

    // Save LLM API keys
    this.api.saveLlmKeys(this.llmKeys()).subscribe({
      next: () => this.notifications.success('Settings saved successfully'),
      error: () => this.notifications.error('Failed to save API keys'),
    });
  }
}
