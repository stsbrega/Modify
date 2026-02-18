import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `
    <div class="auth-page">
      <div class="auth-card">
        <div class="auth-header">
          <div class="logo-mark">M</div>
          <h1>Welcome back</h1>
          <p>Sign in to your Modify account</p>
        </div>

        <form (ngSubmit)="onSubmit()" class="auth-form">
          <div class="form-group">
            <label for="email">Email</label>
            <input
              id="email"
              type="email"
              class="input"
              [(ngModel)]="email"
              name="email"
              placeholder="you@example.com"
              required
            >
          </div>
          <div class="form-group">
            <label for="password">Password</label>
            <input
              id="password"
              type="password"
              class="input"
              [(ngModel)]="password"
              name="password"
              placeholder="Enter your password"
              required
            >
          </div>
          <div class="form-actions">
            <a routerLink="/auth/forgot-password" class="forgot-link">Forgot password?</a>
          </div>
          <button type="submit" class="btn-primary" [disabled]="loading()">
            @if (loading()) {
              <span class="btn-spinner"></span>
              Signing in...
            } @else {
              Sign In
            }
          </button>
        </form>

        <div class="divider">
          <span>or continue with</span>
        </div>

        <div class="oauth-buttons">
          <button class="btn-oauth" (click)="oauthLogin('google')">
            <svg width="18" height="18" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
            Google
          </button>
          <button class="btn-oauth" (click)="oauthLogin('discord')">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="#5865F2"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>
            Discord
          </button>
        </div>

        <p class="auth-footer">
          Don't have an account? <a routerLink="/auth/register">Create one</a>
        </p>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }

    .auth-page {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
      background: var(--color-bg-dark);
      position: relative;
      overflow: hidden;
    }
    .auth-page::before {
      content: '';
      position: absolute;
      top: 20%;
      left: 30%;
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, rgba(196, 165, 90, 0.06) 0%, transparent 70%);
      filter: blur(60px);
      pointer-events: none;
    }
    .auth-page::after {
      content: '';
      position: absolute;
      bottom: 15%;
      right: 25%;
      width: 350px;
      height: 350px;
      background: radial-gradient(circle, rgba(107, 159, 191, 0.04) 0%, transparent 70%);
      filter: blur(60px);
      pointer-events: none;
    }
    .auth-card {
      width: 100%;
      max-width: 400px;
      background: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-xl);
      padding: 2.5rem;
      position: relative;
      z-index: 1;
      box-shadow: var(--shadow-elevated);
      animation: card-enter 0.5s var(--ease-out);
    }
    @keyframes card-enter {
      from { opacity: 0; transform: translateY(16px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .auth-header {
      text-align: center;
      margin-bottom: 2rem;
    }
    .logo-mark {
      width: 48px;
      height: 48px;
      background: var(--color-gold);
      color: #0A0A0C;
      border-radius: 12px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 1.25rem;
      margin-bottom: 1rem;
      font-family: var(--font-display);
      box-shadow: 0 0 20px rgba(196, 165, 90, 0.2);
    }
    .auth-header h1 {
      font-size: 1.375rem;
      font-weight: 600;
      margin-bottom: 0.25rem;
    }
    .auth-header p {
      font-size: 0.875rem;
      color: var(--color-text-muted);
    }

    .auth-form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.375rem;
    }
    .form-group label {
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--color-text-muted);
    }
    .input {
      width: 100%;
      background: var(--color-bg-dark);
      border: 1px solid var(--color-border);
      border-radius: 8px;
      color: var(--color-text);
      padding: 0.625rem 0.875rem;
      font-size: 0.875rem;
      outline: none;
      transition: border-color 0.15s;
    }
    .input:focus {
      border-color: var(--color-gold);
      box-shadow: 0 0 0 3px rgba(196, 165, 90, 0.1);
    }
    .input::placeholder { color: var(--color-text-dim); }

    .form-actions {
      display: flex;
      justify-content: flex-end;
    }
    .forgot-link {
      font-size: 0.8125rem;
      color: var(--color-gold);
      transition: opacity 0.15s;
    }
    .forgot-link:hover { opacity: 0.8; }

    .btn-primary {
      width: 100%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      background: var(--color-gold);
      color: #0D0D0F;
      padding: 0.7rem;
      border-radius: 8px;
      font-weight: 600;
      font-size: 0.875rem;
      transition: background 0.2s, box-shadow 0.3s;
      margin-top: 0.5rem;
    }
    .btn-primary:hover {
      background: var(--color-gold-hover);
      box-shadow: var(--shadow-gold);
      transform: translateY(-1px);
    }
    .btn-primary:active { transform: translateY(0); }
    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
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

    .divider {
      display: flex;
      align-items: center;
      gap: 1rem;
      margin: 1.5rem 0;
    }
    .divider::before, .divider::after {
      content: '';
      flex: 1;
      height: 1px;
      background: var(--color-border);
    }
    .divider span {
      font-size: 0.75rem;
      color: var(--color-text-dim);
      white-space: nowrap;
    }

    .oauth-buttons {
      display: flex;
      gap: 0.75rem;
    }
    .btn-oauth {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      padding: 0.625rem;
      border: 1px solid var(--color-border);
      border-radius: 8px;
      background: transparent;
      color: var(--color-text);
      font-size: 0.8125rem;
      font-weight: 500;
      transition: border-color 0.15s, background 0.15s;
    }
    .btn-oauth:hover {
      border-color: var(--color-border-hover);
      background: rgba(255, 255, 255, 0.03);
    }

    .auth-footer {
      text-align: center;
      margin-top: 1.5rem;
      font-size: 0.8125rem;
      color: var(--color-text-muted);
    }
    .auth-footer a {
      color: var(--color-gold);
      font-weight: 500;
    }
  `],
})
export class LoginComponent {
  email = '';
  password = '';
  loading = signal(false);

  private returnUrl = '/dashboard';

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private notifications: NotificationService,
  ) {
    this.returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/dashboard';
  }

  onSubmit(): void {
    if (!this.email || !this.password) return;
    this.loading.set(true);

    this.authService.login({ email: this.email, password: this.password }).subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigateByUrl(this.returnUrl);
      },
      error: (err) => {
        this.loading.set(false);
        this.notifications.error(err.error?.detail || 'Login failed');
      },
    });
  }

  oauthLogin(provider: 'google' | 'discord'): void {
    this.authService.oauthLogin(provider);
  }
}
