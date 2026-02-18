import { Component, signal, inject, OnInit, OnDestroy, AfterViewInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { trigger, transition, style, animate, query, stagger } from '@angular/animations';
import { AuthService } from '../../core/services/auth.service';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterLink],
  animations: [
    trigger('fadeUp', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(24px)' }),
        animate('600ms cubic-bezier(0.16, 1, 0.3, 1)', style({ opacity: 1, transform: 'translateY(0)' })),
      ]),
    ]),
    trigger('staggerIn', [
      transition(':enter', [
        query('.stagger-item', [
          style({ opacity: 0, transform: 'translateY(20px)' }),
          stagger(100, [
            animate('500ms cubic-bezier(0.16, 1, 0.3, 1)', style({ opacity: 1, transform: 'translateY(0)' })),
          ]),
        ], { optional: true }),
      ]),
    ]),
  ],
  template: `
    <!-- Sticky Navbar -->
    <nav class="navbar" [class.scrolled]="scrolled()">
      <div class="nav-container">
        <a routerLink="/" class="nav-logo">
          <span class="nav-logo-mark">M</span>
          <span class="nav-logo-text">Modify</span>
        </a>
        <div class="nav-links">
          <a href="#features" class="nav-link" (click)="scrollTo($event, 'features')">Features</a>
          <a href="#how-it-works" class="nav-link" (click)="scrollTo($event, 'how-it-works')">How It Works</a>
        </div>
        <div class="nav-actions">
          @if (authService.isLoggedIn()) {
            <a routerLink="/dashboard" class="nav-cta">Dashboard</a>
          } @else {
            <a routerLink="/auth/login" class="nav-link nav-signin">Sign In</a>
            <a routerLink="/auth/register" class="nav-cta">Sign Up</a>
          }
        </div>
      </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-grain"></div>
      <div class="hero-glow hero-glow--gold"></div>
      <div class="hero-glow hero-glow--blue"></div>
      <div class="hero-content" @fadeUp>
        <div class="hero-badge">
          <span class="badge-dot"></span>
          AI-Powered Modding Assistant
        </div>
        <h1 class="hero-title">
          Your Perfect Modlist,<br>
          <span class="hero-title-accent">Built by AI</span>
        </h1>
        <p class="hero-subtitle">
          Tell us your hardware and playstyle. Our AI generates a stable,<br>
          compatible mod list tailored specifically for your setup.
        </p>
        <div class="hero-actions">
          <a routerLink="/setup" class="btn-primary">
            Build My Modlist
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </a>
          <a href="#how-it-works" class="btn-ghost" (click)="scrollTo($event, 'how-it-works')">
            See How It Works
          </a>
        </div>
        <div class="hero-games">
          <span class="hero-games-label">Supporting</span>
          <span class="game-tag game-tag--skyrim">Skyrim SE/AE</span>
          <span class="game-tag game-tag--fallout">Fallout 4</span>
        </div>
      </div>

      <!-- Mock App Preview -->
      <div class="hero-preview" @fadeUp>
        <div class="preview-window">
          <div class="preview-titlebar">
            <div class="preview-dots">
              <span></span><span></span><span></span>
            </div>
            <span class="preview-title">Modify — Modlist Generator</span>
          </div>
          <div class="preview-content">
            <div class="preview-sidebar">
              <div class="preview-sidebar-item active"></div>
              <div class="preview-sidebar-item"></div>
              <div class="preview-sidebar-item"></div>
              <div class="preview-sidebar-item"></div>
            </div>
            <div class="preview-main">
              <div class="preview-header-bar"></div>
              <div class="preview-cards">
                <div class="preview-card">
                  <div class="preview-card-icon gold"></div>
                  <div class="preview-card-lines">
                    <div class="preview-line w60"></div>
                    <div class="preview-line w40 muted"></div>
                  </div>
                  <div class="preview-toggle on"></div>
                </div>
                <div class="preview-card">
                  <div class="preview-card-icon blue"></div>
                  <div class="preview-card-lines">
                    <div class="preview-line w50"></div>
                    <div class="preview-line w70 muted"></div>
                  </div>
                  <div class="preview-toggle on"></div>
                </div>
                <div class="preview-card">
                  <div class="preview-card-icon gold"></div>
                  <div class="preview-card-lines">
                    <div class="preview-line w45"></div>
                    <div class="preview-line w55 muted"></div>
                  </div>
                  <div class="preview-toggle"></div>
                </div>
                <div class="preview-card">
                  <div class="preview-card-icon blue"></div>
                  <div class="preview-card-lines">
                    <div class="preview-line w65"></div>
                    <div class="preview-line w35 muted"></div>
                  </div>
                  <div class="preview-toggle on"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- How It Works -->
    <section class="section" id="how-it-works">
      <div class="section-container">
        <div class="section-header">
          <span class="section-label">How It Works</span>
          <h2 class="section-title">Three steps to your<br>ideal mod setup</h2>
        </div>
        @if (stepsVisible()) {
          <div class="steps" @staggerIn>
            <div class="step stagger-item">
              <div class="step-number">01</div>
              <div class="step-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="2" y="3" width="20" height="14" rx="2"/>
                  <path d="M8 21h8M12 17v4"/>
                </svg>
              </div>
              <h3 class="step-title">Choose Your Game</h3>
              <p class="step-desc">Select Skyrim SE/AE or Fallout 4 and pick your preferred playstyle — survival, combat overhaul, visual enhancement, and more.</p>
            </div>
            <div class="step-divider stagger-item">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </div>
            <div class="step stagger-item">
              <div class="step-number">02</div>
              <div class="step-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2v-4M9 21H5a2 2 0 01-2-2v-4"/>
                </svg>
              </div>
              <h3 class="step-title">Enter Your Specs</h3>
              <p class="step-desc">Paste your hardware info from NVIDIA App or system settings. Our parser auto-detects your GPU, VRAM, CPU, and RAM.</p>
            </div>
            <div class="step-divider stagger-item">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </div>
            <div class="step stagger-item">
              <div class="step-number">03</div>
              <div class="step-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
              </div>
              <h3 class="step-title">Get Your Modlist</h3>
              <p class="step-desc">AI generates a curated, compatible mod list optimized for your hardware tier. Export directly to MO2 or Vortex.</p>
            </div>
          </div>
        }
      </div>
    </section>

    <!-- Features -->
    <section class="section section--dark" id="features">
      <div class="section-container">
        <div class="section-header">
          <span class="section-label">Features</span>
          <h2 class="section-title">Built for modders<br>who know what they want</h2>
        </div>
        @if (featuresVisible()) {
          <div class="features-grid" @staggerIn>
            <div class="feature-card stagger-item">
              <div class="feature-icon feature-icon--gold">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
              </div>
              <h3>AI Compatibility Checking</h3>
              <p>Every mod is checked against your full list for conflicts, missing dependencies, and load order issues before you install anything.</p>
            </div>
            <div class="feature-card stagger-item">
              <div class="feature-icon feature-icon--blue">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="4" y="4" width="16" height="16" rx="2"/>
                  <path d="M9 9h6v6H9z"/>
                  <path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3"/>
                </svg>
              </div>
              <h3>Hardware-Aware Picks</h3>
              <p>Your GPU, VRAM, and CPU tier directly influence which texture resolutions, ENB presets, and script-heavy mods get recommended.</p>
            </div>
            <div class="feature-card stagger-item">
              <div class="feature-icon feature-icon--gold">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
              </div>
              <h3>One-Click Export</h3>
              <p>Export your final mod list as an MO2 profile or Vortex collection. Or download everything straight from Nexus with one click.</p>
            </div>
          </div>
        }
      </div>
    </section>

    <!-- Social Proof -->
    <section class="proof-bar">
      <div class="proof-container">
        <div class="proof-item">
          <span class="proof-number">{{ modlistsGenerated() }}</span>
          <span class="proof-label">Modlists Generated</span>
        </div>
        <div class="proof-divider"></div>
        <div class="proof-item">
          <span class="proof-number">{{ gamesSupported() }}</span>
          <span class="proof-label">Games Supported</span>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="section cta-section">
      <div class="section-container" style="text-align: center;">
        <h2 class="cta-title">Ready to build your<br>perfect mod setup?</h2>
        <p class="cta-subtitle">Create a free account and save your hardware profile for instant modlists.</p>
        <a routerLink="/auth/register" class="btn-primary btn-primary--lg">
          Create Free Account
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </a>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-container">
        <div class="footer-brand">
          <span class="nav-logo-mark">M</span>
          <span class="footer-text">Modify</span>
        </div>
        <div class="footer-links">
          <a routerLink="/dashboard">Dashboard</a>
          <a routerLink="/browse">Browse Mods</a>
          <a routerLink="/settings">Settings</a>
        </div>
        <p class="footer-copy">&copy; 2026 Modify. Open source under GPL-3.0.</p>
      </div>
    </footer>
  `,
  styles: [`
    :host {
      display: block;
    }

    /* ===== Navbar ===== */
    .navbar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 200;
      padding: 0 2rem;
      height: 64px;
      transition: background 0.3s, border-color 0.3s, backdrop-filter 0.3s;
    }
    .navbar.scrolled {
      background: rgba(13, 13, 15, 0.85);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--color-border);
    }
    .nav-container {
      max-width: var(--max-width);
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 100%;
    }
    .nav-logo {
      display: flex;
      align-items: center;
      gap: 0.625rem;
      color: var(--color-text);
    }
    .nav-logo-mark {
      width: 32px;
      height: 32px;
      background: var(--color-gold);
      color: #0D0D0F;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 1rem;
      font-family: var(--font-display);
    }
    .nav-logo-text {
      font-size: 1.125rem;
      font-weight: 600;
      letter-spacing: -0.01em;
    }
    .nav-links {
      display: flex;
      gap: 2rem;
    }
    .nav-link {
      color: var(--color-text-muted);
      font-size: 0.875rem;
      font-weight: 500;
      transition: color 0.15s;
    }
    .nav-link:hover { color: var(--color-text); }
    .nav-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .nav-signin {
      color: var(--color-text-muted);
      font-size: 0.875rem;
      font-weight: 500;
      transition: color 0.15s;
    }
    .nav-signin:hover { color: var(--color-text); }
    .nav-cta {
      background: var(--color-gold);
      color: #0D0D0F;
      padding: 0.5rem 1.25rem;
      border-radius: 8px;
      font-size: 0.8125rem;
      font-weight: 600;
      transition: background 0.2s, box-shadow 0.2s;
    }
    .nav-cta:hover {
      background: var(--color-gold-hover);
      box-shadow: 0 4px 20px rgba(196, 165, 90, 0.25);
    }

    /* ===== Hero ===== */
    .hero {
      position: relative;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 120px 2rem 80px;
      overflow: hidden;
    }
    .hero-grain {
      position: absolute;
      inset: 0;
      opacity: 0.06;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
      background-repeat: repeat;
      pointer-events: none;
    }
    .hero-glow {
      position: absolute;
      width: 650px;
      height: 650px;
      border-radius: 50%;
      filter: blur(130px);
      pointer-events: none;
      animation: glow-drift 12s ease-in-out infinite;
    }
    .hero-glow--gold {
      top: 5%;
      left: 12%;
      background: radial-gradient(circle, var(--color-gold-glow) 0%, transparent 70%);
      opacity: 0.6;
    }
    .hero-glow--blue {
      bottom: 8%;
      right: 8%;
      background: radial-gradient(circle, var(--color-blue-glow) 0%, transparent 70%);
      opacity: 0.5;
      animation-delay: -6s;
      animation-direction: reverse;
    }
    @keyframes glow-drift {
      0%, 100% { transform: translate(0, 0) scale(1); }
      33% { transform: translate(20px, -15px) scale(1.05); }
      66% { transform: translate(-10px, 10px) scale(0.95); }
    }
    .hero-content {
      position: relative;
      z-index: 1;
      text-align: center;
      max-width: 720px;
    }
    .hero-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(196, 165, 90, 0.08);
      border: 1px solid rgba(196, 165, 90, 0.18);
      color: var(--color-gold);
      padding: 0.375rem 1rem;
      border-radius: 100px;
      font-size: 0.8125rem;
      font-weight: 500;
      margin-bottom: 2rem;
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
    }
    .badge-dot {
      width: 6px;
      height: 6px;
      background: var(--color-gold);
      border-radius: 50%;
      animation: pulse-dot 2s ease-in-out infinite;
    }
    @keyframes pulse-dot {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
    .hero-title {
      font-family: var(--font-display);
      font-size: clamp(2.5rem, 5.5vw, 4.25rem);
      font-weight: 500;
      line-height: 1.1;
      letter-spacing: -0.02em;
      margin-bottom: 1.5rem;
      color: var(--color-text);
    }
    .hero-title-accent {
      background: linear-gradient(135deg, var(--color-gold) 0%, var(--color-gold-hover) 40%, var(--color-blue) 100%);
      background-size: 200% auto;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      animation: gradient-shift 6s ease-in-out infinite;
    }
    @keyframes gradient-shift {
      0%, 100% { background-position: 0% center; }
      50% { background-position: 100% center; }
    }
    .hero-subtitle {
      font-size: 1.125rem;
      color: var(--color-text-muted);
      line-height: 1.7;
      margin-bottom: 2.5rem;
    }
    .hero-actions {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 1rem;
      margin-bottom: 3rem;
    }

    /* Buttons */
    .btn-primary {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: var(--color-gold);
      color: #0D0D0F;
      padding: 0.75rem 1.75rem;
      border-radius: 10px;
      font-size: 0.9375rem;
      font-weight: 600;
      transition: background 0.2s, box-shadow 0.3s, transform 0.15s;
    }
    .btn-primary:hover {
      background: var(--color-gold-hover);
      box-shadow: 0 4px 24px rgba(196, 165, 90, 0.3), 0 0 8px rgba(196, 165, 90, 0.15);
      transform: translateY(-2px);
    }
    .btn-primary:active {
      transform: translateY(0);
      box-shadow: 0 2px 12px rgba(196, 165, 90, 0.2);
    }
    .btn-primary--lg {
      padding: 0.875rem 2.25rem;
      font-size: 1rem;
    }
    .btn-ghost {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      color: var(--color-text-muted);
      padding: 0.75rem 1.5rem;
      border-radius: 10px;
      font-size: 0.9375rem;
      font-weight: 500;
      border: 1px solid var(--color-border);
      transition: color 0.2s, border-color 0.2s, background 0.2s;
    }
    .btn-ghost:hover {
      color: var(--color-text);
      border-color: var(--color-border-hover);
      background: rgba(255, 255, 255, 0.03);
    }

    /* Game tags */
    .hero-games {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.75rem;
    }
    .hero-games-label {
      font-size: 0.8125rem;
      color: var(--color-text-dim);
      font-weight: 500;
    }
    .game-tag {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.25rem 0.75rem;
      border-radius: 6px;
      letter-spacing: 0.03em;
    }
    .game-tag--skyrim {
      background: rgba(123, 164, 192, 0.12);
      color: var(--color-blue);
      border: 1px solid rgba(123, 164, 192, 0.2);
    }
    .game-tag--fallout {
      background: rgba(192, 160, 96, 0.12);
      color: var(--color-gold);
      border: 1px solid rgba(192, 160, 96, 0.2);
    }

    /* ===== Mock Preview ===== */
    .hero-preview {
      position: relative;
      z-index: 1;
      width: 100%;
      max-width: 800px;
      margin-top: 4rem;
    }
    .preview-window {
      background: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 24px 80px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.03) inset;
      animation: subtle-float 8s ease-in-out infinite;
    }
    @keyframes subtle-float {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-6px); }
    }
    .preview-titlebar {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.75rem 1rem;
      background: var(--color-bg-elevated);
      border-bottom: 1px solid var(--color-border);
    }
    .preview-dots {
      display: flex;
      gap: 6px;
    }
    .preview-dots span {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.1);
    }
    .preview-dots span:first-child { background: #ef4444; }
    .preview-dots span:nth-child(2) { background: #eab308; }
    .preview-dots span:last-child { background: #22c55e; }
    .preview-title {
      font-size: 0.75rem;
      color: var(--color-text-dim);
    }
    .preview-content {
      display: flex;
      min-height: 280px;
    }
    .preview-sidebar {
      width: 56px;
      background: rgba(255, 255, 255, 0.02);
      border-right: 1px solid var(--color-border);
      padding: 1rem 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.75rem;
    }
    .preview-sidebar-item {
      width: 28px;
      height: 28px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.05);
    }
    .preview-sidebar-item.active {
      background: var(--color-gold);
      opacity: 0.6;
    }
    .preview-main {
      flex: 1;
      padding: 1.25rem;
    }
    .preview-header-bar {
      height: 12px;
      width: 40%;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      margin-bottom: 1.25rem;
    }
    .preview-cards {
      display: flex;
      flex-direction: column;
      gap: 0.625rem;
    }
    .preview-card {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem;
      background: rgba(255, 255, 255, 0.025);
      border: 1px solid var(--color-border);
      border-radius: 8px;
    }
    .preview-card-icon {
      width: 32px;
      height: 32px;
      border-radius: 6px;
      flex-shrink: 0;
    }
    .preview-card-icon.gold { background: rgba(192, 160, 96, 0.2); }
    .preview-card-icon.blue { background: rgba(123, 164, 192, 0.2); }
    .preview-card-lines {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .preview-line {
      height: 8px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
    }
    .preview-line.muted { background: rgba(255, 255, 255, 0.05); }
    .preview-line.w35 { width: 35%; }
    .preview-line.w40 { width: 40%; }
    .preview-line.w45 { width: 45%; }
    .preview-line.w50 { width: 50%; }
    .preview-line.w55 { width: 55%; }
    .preview-line.w60 { width: 60%; }
    .preview-line.w65 { width: 65%; }
    .preview-line.w70 { width: 70%; }
    .preview-toggle {
      width: 32px;
      height: 18px;
      border-radius: 9px;
      background: rgba(255, 255, 255, 0.08);
      flex-shrink: 0;
    }
    .preview-toggle.on { background: rgba(192, 160, 96, 0.4); }

    /* ===== Sections ===== */
    .section {
      padding: 6rem 2rem;
    }
    .section--dark {
      background: var(--color-bg-card);
    }
    .section-container {
      max-width: var(--max-width);
      margin: 0 auto;
    }
    .section-header {
      text-align: center;
      margin-bottom: 4rem;
    }
    .section-label {
      display: inline-block;
      font-size: 0.8125rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--color-gold);
      margin-bottom: 1rem;
    }
    .section-title {
      font-family: var(--font-display);
      font-size: clamp(1.75rem, 3vw, 2.5rem);
      font-weight: 500;
      line-height: 1.2;
      color: var(--color-text);
    }

    /* ===== Steps ===== */
    .steps {
      display: flex;
      align-items: flex-start;
      justify-content: center;
      gap: 2rem;
    }
    .step {
      flex: 1;
      max-width: 320px;
      text-align: center;
    }
    .step-number {
      font-family: var(--font-display);
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--color-gold);
      margin-bottom: 1.25rem;
      letter-spacing: 0.05em;
    }
    .step-icon {
      width: 56px;
      height: 56px;
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--color-border);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 1.25rem;
      color: var(--color-text);
      transition: border-color 0.25s, box-shadow 0.25s, background 0.25s;
    }
    .step:hover .step-icon {
      border-color: rgba(196, 165, 90, 0.25);
      box-shadow: 0 0 20px rgba(196, 165, 90, 0.1);
      background: rgba(196, 165, 90, 0.06);
    }
    .step-title {
      font-size: 1.125rem;
      font-weight: 600;
      margin-bottom: 0.625rem;
    }
    .step-desc {
      font-size: 0.875rem;
      color: var(--color-text-muted);
      line-height: 1.6;
    }
    .step-divider {
      display: flex;
      align-items: center;
      color: var(--color-text-dim);
      padding-top: 4.5rem;
    }

    /* ===== Features Grid ===== */
    .features-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1.5rem;
    }
    .feature-card {
      background: var(--color-bg-dark);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-lg);
      padding: 2rem;
      transition: border-color 0.25s, transform 0.3s var(--ease-out), box-shadow 0.3s;
      position: relative;
    }
    .feature-card::before {
      content: '';
      position: absolute;
      inset: 0;
      border-radius: inherit;
      background: radial-gradient(ellipse at 50% 0%, rgba(196, 165, 90, 0.04) 0%, transparent 70%);
      opacity: 0;
      transition: opacity 0.3s;
      pointer-events: none;
    }
    .feature-card:hover {
      border-color: rgba(196, 165, 90, 0.15);
      transform: translateY(-4px);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(196, 165, 90, 0.08);
    }
    .feature-card:hover::before {
      opacity: 1;
    }
    .feature-icon {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 1.25rem;
    }
    .feature-icon--gold {
      background: rgba(192, 160, 96, 0.12);
      color: var(--color-gold);
    }
    .feature-icon--blue {
      background: rgba(123, 164, 192, 0.12);
      color: var(--color-blue);
    }
    .feature-card h3 {
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
    }
    .feature-card p {
      font-size: 0.875rem;
      color: var(--color-text-muted);
      line-height: 1.6;
    }

    /* ===== Social Proof Bar ===== */
    .proof-bar {
      border-top: 1px solid var(--color-border);
      border-bottom: 1px solid var(--color-border);
      padding: 3rem 2rem;
    }
    .proof-container {
      max-width: var(--max-width);
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 3rem;
    }
    .proof-item {
      text-align: center;
    }
    .proof-number {
      display: block;
      font-family: var(--font-display);
      font-size: 1.75rem;
      font-weight: 600;
      color: var(--color-text);
      margin-bottom: 0.25rem;
      background: linear-gradient(180deg, var(--color-text) 0%, var(--color-text-muted) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .proof-label {
      font-size: 0.8125rem;
      color: var(--color-text-muted);
    }
    .proof-divider {
      width: 1px;
      height: 40px;
      background: var(--color-border);
    }

    /* ===== CTA Section ===== */
    .cta-section {
      padding: 8rem 2rem;
      position: relative;
      overflow: hidden;
    }
    .cta-section::before {
      content: '';
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 600px;
      height: 400px;
      background: radial-gradient(ellipse, rgba(196, 165, 90, 0.06) 0%, transparent 70%);
      pointer-events: none;
    }
    .cta-title {
      font-family: var(--font-display);
      font-size: clamp(1.75rem, 3vw, 2.5rem);
      font-weight: 500;
      line-height: 1.2;
      margin-bottom: 1rem;
    }
    .cta-subtitle {
      font-size: 1.0625rem;
      color: var(--color-text-muted);
      margin-bottom: 2.5rem;
    }

    /* ===== Footer ===== */
    .footer {
      border-top: 1px solid var(--color-border);
      padding: 2.5rem 2rem;
    }
    .footer-container {
      max-width: var(--max-width);
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .footer-brand {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .footer-text {
      font-size: 1rem;
      font-weight: 600;
    }
    .footer-links {
      display: flex;
      gap: 2rem;
    }
    .footer-links a {
      font-size: 0.8125rem;
      color: var(--color-text-muted);
      transition: color 0.15s;
    }
    .footer-links a:hover { color: var(--color-text); }
    .footer-copy {
      font-size: 0.75rem;
      color: var(--color-text-dim);
    }

    /* ===== Responsive ===== */
    @media (max-width: 768px) {
      .steps {
        flex-direction: column;
        align-items: center;
      }
      .step-divider {
        padding-top: 0;
        transform: rotate(90deg);
      }
      .features-grid {
        grid-template-columns: 1fr;
      }
      .proof-container {
        flex-direction: column;
        gap: 1.5rem;
      }
      .proof-divider {
        width: 40px;
        height: 1px;
      }
      .footer-container {
        flex-direction: column;
        gap: 1.5rem;
        text-align: center;
      }
      .hero-subtitle br { display: none; }
      .nav-links { display: none; }
    }
  `],
})
export class LandingComponent implements OnInit, OnDestroy, AfterViewInit {
  scrolled = signal(false);
  stepsVisible = signal(false);
  featuresVisible = signal(false);
  modlistsGenerated = signal('0');
  gamesSupported = signal('2');

  private apiService = inject(ApiService);

  constructor(public authService: AuthService) {}

  private scrollHandler = () => {
    this.scrolled.set(window.scrollY > 20);
  };

  private observer?: IntersectionObserver;

  ngOnInit(): void {
    window.addEventListener('scroll', this.scrollHandler, { passive: true });
    this.scrollHandler();

    this.apiService.getStats().subscribe({
      next: (stats) => {
        this.modlistsGenerated.set(stats.modlists_generated.toLocaleString());
        this.gamesSupported.set(stats.games_supported.toString());
      },
      error: () => {},
    });
  }

  ngAfterViewInit(): void {
    this.observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = entry.target.id;
            if (id === 'how-it-works') this.stepsVisible.set(true);
            if (id === 'features') this.featuresVisible.set(true);
          }
        });
      },
      { threshold: 0.15 },
    );

    const howItWorks = document.getElementById('how-it-works');
    const features = document.getElementById('features');
    if (howItWorks) this.observer.observe(howItWorks);
    if (features) this.observer.observe(features);
  }

  ngOnDestroy(): void {
    window.removeEventListener('scroll', this.scrollHandler);
    this.observer?.disconnect();
  }

  scrollTo(event: Event, id: string): void {
    event.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  }
}
