import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject, Injector } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

const TOKEN_KEY = 'access_token';
let isRefreshing = false;

export const authInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  // Inject Injector instead of AuthService directly to break circular DI:
  // AuthService → HttpClient → authInterceptor → AuthService
  const injector = inject(Injector);

  // Skip auth header for auth endpoints (except /me and /me/hardware)
  const isAuthEndpoint =
    req.url.includes('/auth/login') ||
    req.url.includes('/auth/register') ||
    req.url.includes('/auth/refresh') ||
    req.url.includes('/auth/verify-email') ||
    req.url.includes('/auth/forgot-password') ||
    req.url.includes('/auth/reset-password') ||
    req.url.includes('/auth/oauth/');

  // Read token directly from localStorage — avoids injecting AuthService
  let authReq = req;
  const token = localStorage.getItem(TOKEN_KEY);
  if (token && !isAuthEndpoint) {
    authReq = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // 401 = expired/invalid token
      // 403 with no token = missing Authorization header (HTTPBearer auto_error)
      const currentToken = localStorage.getItem(TOKEN_KEY);
      const shouldRefresh =
        error.status === 401 ||
        (error.status === 403 && !currentToken);
      if (shouldRefresh && !isAuthEndpoint && !isRefreshing) {
        isRefreshing = true;
        // Lazily resolve AuthService — safe here because it's fully constructed by now
        const authService = injector.get(AuthService);
        return authService.refreshToken().pipe(
          switchMap((res) => {
            isRefreshing = false;
            const retryReq = req.clone({
              setHeaders: { Authorization: `Bearer ${res.access_token}` },
            });
            return next(retryReq);
          }),
          catchError((refreshError) => {
            isRefreshing = false;
            authService.logout();
            return throwError(() => refreshError);
          }),
        );
      }
      return throwError(() => error);
    }),
  );
};
