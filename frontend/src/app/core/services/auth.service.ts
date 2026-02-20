import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { map, Observable, tap } from 'rxjs';
import {
  User,
  TokenResponse,
  RegisterRequest,
  LoginRequest,
  UserHardware,
  HardwareUpdateRequest,
  OAuthProviderInfo,
} from '../../shared/models/auth.model';

const TOKEN_KEY = 'access_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private baseUrl = (window as any).__env?.API_URL || '/api';
  private _user = signal<User | null>(null);

  readonly user = this._user.asReadonly();
  readonly isLoggedIn = computed(() => !!this._user());
  readonly isEmailVerified = computed(() => this._user()?.email_verified ?? false);

  constructor(
    private http: HttpClient,
    private router: Router,
  ) {
    // Attempt to load profile if we have a stored token
    if (this.getAccessToken()) {
      this.loadProfile();
    }
  }

  // --- Token Management ---

  getAccessToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  setAccessToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  }

  clearAccessToken(): void {
    localStorage.removeItem(TOKEN_KEY);
  }

  // --- Auth Endpoints ---

  register(data: RegisterRequest): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${this.baseUrl}/auth/register`, data, { withCredentials: true })
      .pipe(
        tap((res) => {
          this.setAccessToken(res.access_token);
          this.loadProfile();
        }),
      );
  }

  login(data: LoginRequest): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${this.baseUrl}/auth/login`, data, { withCredentials: true })
      .pipe(
        tap((res) => {
          this.setAccessToken(res.access_token);
          this.loadProfile();
        }),
      );
  }

  refreshToken(): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${this.baseUrl}/auth/refresh`, {}, { withCredentials: true })
      .pipe(
        tap((res) => {
          this.setAccessToken(res.access_token);
        }),
      );
  }

  logout(): void {
    this.http
      .post(`${this.baseUrl}/auth/logout`, {}, { withCredentials: true })
      .subscribe({ error: () => {} });
    this.clearAccessToken();
    this._user.set(null);
    this.router.navigate(['/auth/login']);
  }

  // --- Profile ---

  loadProfile(): void {
    this.loadProfileAsync().subscribe();
  }

  loadProfileAsync(): Observable<User> {
    return this.http.get<User>(`${this.baseUrl}/auth/me`).pipe(
      tap({
        next: (user) => this._user.set(user),
        error: () => {
          this.clearAccessToken();
          this._user.set(null);
        },
      }),
    );
  }

  updateProfile(data: { display_name?: string; avatar_url?: string }): Observable<User> {
    return this.http.put<User>(`${this.baseUrl}/auth/me`, data).pipe(
      tap((user) => this._user.set(user)),
    );
  }

  // --- Hardware ---

  getHardware(): Observable<UserHardware | null> {
    return this.http.get<UserHardware | null>(`${this.baseUrl}/auth/me/hardware`);
  }

  saveHardware(data: HardwareUpdateRequest): Observable<UserHardware> {
    return this.http.put<UserHardware>(`${this.baseUrl}/auth/me/hardware`, data).pipe(
      tap((hw) => {
        const current = this._user();
        if (current) {
          this._user.set({ ...current, hardware: hw });
        }
      }),
    );
  }

  get savedHardware(): UserHardware | undefined {
    return this._user()?.hardware ?? undefined;
  }

  // --- OAuth ---

  getOAuthProviders(): Observable<string[]> {
    return this.http
      .get<{ providers: string[] }>(`${this.baseUrl}/auth/oauth/providers`)
      .pipe(map((res) => res.providers));
  }

  oauthLogin(provider: 'google' | 'discord'): void {
    this.http
      .get<{ authorization_url: string }>(`${this.baseUrl}/auth/oauth/${provider}`)
      .subscribe({
        next: (res) => {
          window.location.href = res.authorization_url;
        },
        error: () => {}, // Notification already shown by errorInterceptor
      });
  }

  // --- Connected Accounts ---

  getConnectedAccounts(): Observable<OAuthProviderInfo[]> {
    return this.http.get<OAuthProviderInfo[]>(`${this.baseUrl}/auth/me/connected-accounts`);
  }

  disconnectAccount(provider: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/auth/me/connected-accounts/${provider}`);
  }

  // --- Email Verification ---

  verifyEmail(token: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/verify-email`, { token });
  }

  resendVerification(): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/resend-verification`, {});
  }

  // --- Password Reset ---

  forgotPassword(email: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/forgot-password`, { email });
  }

  resetPassword(token: string, newPassword: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/reset-password`, {
      token,
      new_password: newPassword,
    });
  }
}
