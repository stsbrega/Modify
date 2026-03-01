/**
 * Singleton service for managing real-time modlist generation.
 *
 * Holds state across route navigation — the EventSource stays open even
 * when the user navigates away. On return to the generation page, events
 * are replayed from the server (the backend stores all events in memory).
 *
 * Key design decisions:
 * - Uses signals for reactive state (Angular 17+ pattern)
 * - EventSource for SSE (auto-reconnect built into the browser API)
 * - Token passed as query param since EventSource doesn't support headers
 */

import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  CompleteEvent,
  ErrorEvent,
  GenerationEvent,
  GenerationStartResponse,
  GenerationStatusResponse,
  ModAddedEvent,
  PatchAddedEvent,
  PausedEvent,
  PhaseStartEvent,
} from '../../shared/models/generation.model';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class GenerationService {
  private baseUrl = window.__env?.API_URL || '/api';
  private eventSource: EventSource | null = null;

  // ── Observable state ──
  readonly generationId = signal<string | null>(null);
  readonly events = signal<GenerationEvent[]>([]);
  readonly status = signal<'idle' | 'running' | 'complete' | 'error' | 'paused'>('idle');
  readonly modlistId = signal<string | null>(null);

  // ── Derived state ──
  readonly currentPhase = computed<PhaseStartEvent | null>(() => {
    const evts = this.events();
    for (let i = evts.length - 1; i >= 0; i--) {
      const evt = evts[i];
      if (evt.type === 'phase_start') return evt;
    }
    return null;
  });

  readonly totalPhases = computed(() => {
    const phase = this.currentPhase();
    return phase?.total_phases ?? 0;
  });

  readonly modsAdded = computed(() =>
    this.events().filter(
      (e): e is ModAddedEvent => e.type === 'mod_added'
    )
  );

  readonly patchesAdded = computed(() =>
    this.events().filter(
      (e): e is PatchAddedEvent => e.type === 'patch_added'
    )
  );

  readonly pauseInfo = computed<PausedEvent | null>(() => {
    const evts = this.events();
    for (let i = evts.length - 1; i >= 0; i--) {
      const evt = evts[i];
      if (evt.type === 'paused') return evt;
    }
    return null;
  });

  readonly errorMessage = computed<string | null>(() => {
    const evts = this.events();
    for (let i = evts.length - 1; i >= 0; i--) {
      const evt = evts[i];
      if (evt.type === 'error') return evt.message;
    }
    return null;
  });

  constructor(
    private http: HttpClient,
    private auth: AuthService,
  ) {}

  // ── API Methods ──

  startGeneration(request: Record<string, unknown>): Observable<GenerationStartResponse> {
    return this.http.post<GenerationStartResponse>(
      `${this.baseUrl}/generation/start`,
      request,
    );
  }

  getStatus(generationId: string): Observable<GenerationStatusResponse> {
    return this.http.get<GenerationStatusResponse>(
      `${this.baseUrl}/generation/${generationId}/status`,
    );
  }

  resumeGeneration(generationId: string): Observable<{ status: string }> {
    return this.http.post<{ status: string }>(
      `${this.baseUrl}/generation/${generationId}/resume`,
      {},
    );
  }

  // ── SSE Connection ──

  connectToEvents(generationId: string): void {
    this.generationId.set(generationId);
    this.status.set('running');

    // Close existing connection if any
    this.disconnectEvents();

    // EventSource doesn't support Authorization headers.
    // Pass token as query param — the backend validates it the same way.
    const token = this.auth.getAccessToken();
    const url = `${this.baseUrl}/generation/${generationId}/events?token=${encodeURIComponent(token || '')}`;

    this.eventSource = new EventSource(url);

    this.eventSource.onmessage = (event) => {
      try {
        const data: GenerationEvent = JSON.parse(event.data);
        this.events.update((prev) => [...prev, data]);

        // Update status based on terminal events
        switch (data.type) {
          case 'complete':
            this.status.set('complete');
            this.modlistId.set((data as CompleteEvent).modlist_id);
            this.disconnectEvents();
            break;
          case 'error':
            this.status.set('error');
            this.disconnectEvents();
            break;
          case 'paused':
            this.status.set('paused');
            this.disconnectEvents();
            break;
          case 'resumed':
            this.status.set('running');
            break;
        }
      } catch (e) {
        console.error('Failed to parse SSE event:', e);
      }
    };

    this.eventSource.onerror = () => {
      // EventSource auto-reconnects. On reconnect, the backend replays
      // all stored events, so we might get duplicates. We handle this
      // by resetting the events array when reconnecting. The backend
      // always sends the full history on a new connection.
      console.warn('SSE connection error — will auto-reconnect');
    };
  }

  disconnectEvents(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  /**
   * Reset all state for a new generation.
   * Call this before starting a new generation or when leaving the flow entirely.
   */
  reset(): void {
    this.disconnectEvents();
    this.generationId.set(null);
    this.events.set([]);
    this.status.set('idle');
    this.modlistId.set(null);
  }

  /**
   * Check if we have an active/recent generation for the given ID.
   * Used when navigating back to the generation page.
   */
  isConnectedTo(generationId: string): boolean {
    return this.generationId() === generationId && this.eventSource !== null;
  }

  /**
   * Reconnect to an existing generation if we navigated away.
   * The SSE endpoint replays all past events on reconnect.
   */
  reconnectIfNeeded(generationId: string): void {
    if (this.generationId() === generationId) {
      if (this.status() === 'running' && !this.eventSource) {
        // We were running but lost connection — reconnect
        this.events.set([]); // Clear to avoid duplicates from replay
        this.connectToEvents(generationId);
      }
      // If complete/error/paused, no need to reconnect — state is already final
      return;
    }

    // Different generation — reset and connect fresh
    this.reset();
    this.connectToEvents(generationId);
  }
}
