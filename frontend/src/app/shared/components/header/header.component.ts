import { Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <header class="header">
      <div class="header-content">
        <a routerLink="/" class="logo">
          <span class="logo-mark">MO</span>
          <span class="logo-text">ModdersOmni</span>
        </a>
        <nav class="nav">
          <a routerLink="/dashboard" routerLinkActive="active" class="nav-link">Dashboard</a>
          <a routerLink="/browse" routerLinkActive="active" class="nav-link">Browse</a>
          <a routerLink="/setup" routerLinkActive="active" class="nav-link">New Build</a>
          <a routerLink="/downloads" routerLinkActive="active" class="nav-link">Downloads</a>
          <a routerLink="/settings" routerLinkActive="active" class="nav-link">Settings</a>
        </nav>
        <div class="header-actions">
          @if (authService.isLoggedIn()) {
            <div class="user-menu">
              <button class="avatar-btn" (click)="menuOpen.set(!menuOpen())" title="Profile">
                @if (userInitials()) {
                  <span class="avatar-initials">{{ userInitials() }}</span>
                } @else {
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="8" r="4"/>
                    <path d="M5.5 21c0-3.5 2.9-6 6.5-6s6.5 2.5 6.5 6"/>
                  </svg>
                }
              </button>
              @if (menuOpen()) {
                <div class="dropdown" (click)="menuOpen.set(false)">
                  <div class="dropdown-header">
                    <span class="dropdown-name">{{ authService.user()?.display_name || 'User' }}</span>
                    <span class="dropdown-email">{{ authService.user()?.email }}</span>
                  </div>
                  <div class="dropdown-divider"></div>
                  <a routerLink="/settings" class="dropdown-item">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                      <circle cx="12" cy="12" r="3"/>
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                    </svg>
                    Settings
                  </a>
                  <button class="dropdown-item dropdown-item--danger" (click)="logout()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                      <polyline points="16 17 21 12 16 7"/>
                      <line x1="21" y1="12" x2="9" y2="12"/>
                    </svg>
                    Sign Out
                  </button>
                </div>
                <div class="dropdown-backdrop" (click)="menuOpen.set(false)"></div>
              }
            </div>
          } @else {
            <a routerLink="/auth/login" class="sign-in-btn">Sign In</a>
          }
        </div>
      </div>
    </header>
  `,
  styles: [`
    .header {
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(13, 13, 15, 0.8);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--color-border);
      height: var(--header-height);
    }
    .header-content {
      max-width: var(--max-width);
      margin: 0 auto;
      padding: 0 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 100%;
    }
    .logo {
      display: flex;
      align-items: center;
      gap: 0.625rem;
      color: var(--color-text);
      transition: gap 0.2s var(--ease-out);
    }
    .logo:hover { gap: 0.75rem; }
    .logo-mark {
      width: 32px;
      height: 32px;
      background: var(--color-gold);
      color: #0A0A0C;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 1rem;
      font-family: var(--font-display);
      transition: box-shadow 0.25s, transform 0.2s;
    }
    .logo:hover .logo-mark {
      box-shadow: 0 0 16px rgba(196, 165, 90, 0.3);
      transform: scale(1.05);
    }
    .logo-text {
      font-size: 1.125rem;
      font-weight: 600;
      letter-spacing: -0.01em;
    }
    .nav {
      display: flex;
      gap: 0.25rem;
    }
    .nav-link {
      color: var(--color-text-muted);
      font-size: 0.8125rem;
      font-weight: 500;
      padding: 0.375rem 0.75rem;
      border-radius: 6px;
      transition: color 0.15s, background 0.15s;
    }
    .nav-link:hover {
      color: var(--color-text);
      background: rgba(255, 255, 255, 0.05);
    }
    .nav-link.active {
      color: var(--color-gold);
      background: rgba(196, 165, 90, 0.08);
    }
    .header-actions {
      display: flex;
      align-items: center;
    }

    /* Sign In Button */
    .sign-in-btn {
      background: var(--color-gold);
      color: #0D0D0F;
      padding: 0.4rem 1rem;
      border-radius: 8px;
      font-size: 0.8125rem;
      font-weight: 600;
      transition: background 0.2s, box-shadow 0.2s;
    }
    .sign-in-btn:hover {
      background: var(--color-gold-hover);
      box-shadow: 0 4px 20px rgba(196, 165, 90, 0.25);
    }

    /* User Menu */
    .user-menu {
      position: relative;
    }
    .avatar-btn {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: var(--color-bg-elevated);
      border: 1px solid var(--color-border);
      color: var(--color-text-muted);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: border-color 0.15s, color 0.15s;
      cursor: pointer;
    }
    .avatar-btn:hover {
      border-color: rgba(196, 165, 90, 0.3);
      color: var(--color-gold);
      box-shadow: 0 0 12px rgba(196, 165, 90, 0.12);
    }
    .avatar-initials {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--color-gold);
      text-transform: uppercase;
    }

    /* Dropdown */
    .dropdown-backdrop {
      position: fixed;
      inset: 0;
      z-index: 99;
    }
    .dropdown {
      position: absolute;
      right: 0;
      top: calc(100% + 8px);
      width: 220px;
      background: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-md);
      padding: 0.5rem;
      z-index: 100;
      box-shadow: var(--shadow-elevated);
      animation: dropdown-enter 0.2s var(--ease-out);
      transform-origin: top right;
    }
    @keyframes dropdown-enter {
      from { opacity: 0; transform: scale(0.95) translateY(-4px); }
      to { opacity: 1; transform: scale(1) translateY(0); }
    }
    .dropdown-header {
      padding: 0.5rem 0.625rem;
      display: flex;
      flex-direction: column;
      gap: 0.125rem;
    }
    .dropdown-name {
      font-size: 0.8125rem;
      font-weight: 600;
    }
    .dropdown-email {
      font-size: 0.75rem;
      color: var(--color-text-muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .dropdown-divider {
      height: 1px;
      background: var(--color-border);
      margin: 0.375rem 0;
    }
    .dropdown-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      width: 100%;
      padding: 0.5rem 0.625rem;
      border-radius: 6px;
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--color-text-muted);
      transition: color 0.15s, background 0.15s;
      text-decoration: none;
      background: none;
      border: none;
      cursor: pointer;
      text-align: left;
    }
    .dropdown-item:hover {
      color: var(--color-text);
      background: rgba(255, 255, 255, 0.04);
    }
    .dropdown-item--danger:hover {
      color: #ef4444;
    }
  `],
})
export class HeaderComponent {
  menuOpen = signal(false);

  constructor(public authService: AuthService) {}

  userInitials(): string {
    const user = this.authService.user();
    if (!user) return '';
    const name = user.display_name || user.email;
    const parts = name.split(/[\s@]+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.substring(0, 2).toUpperCase();
  }

  logout(): void {
    this.menuOpen.set(false);
    this.authService.logout();
  }
}
