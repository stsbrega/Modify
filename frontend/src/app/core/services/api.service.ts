import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Game, Playstyle } from '../../shared/models/game.model';
import { HardwareSpecs, SpecsParseResponse } from '../../shared/models/specs.model';
import { Modlist, DownloadStatus } from '../../shared/models/mod.model';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private baseUrl = (window as any).__env?.API_URL || '/api';

  constructor(private http: HttpClient) {}

  // Games
  getGames(): Observable<Game[]> {
    return this.http.get<Game[]>(`${this.baseUrl}/games/`);
  }

  getPlaystyles(gameId: number): Observable<Playstyle[]> {
    return this.http.get<Playstyle[]>(`${this.baseUrl}/games/${gameId}/playstyles`);
  }

  // Hardware Specs
  parseSpecs(rawText: string): Observable<SpecsParseResponse> {
    return this.http.post<SpecsParseResponse>(`${this.baseUrl}/specs/parse`, {
      raw_text: rawText,
    });
  }

  // Modlist
  generateModlist(request: {
    game_id: number;
    playstyle_id: number;
    game_version?: string;
    gpu?: string;
    vram_mb?: number;
    cpu?: string;
    ram_gb?: number;
    cpu_cores?: number;
    cpu_speed_ghz?: number;
  }): Observable<Modlist> {
    return this.http.post<Modlist>(`${this.baseUrl}/modlist/generate`, request);
  }

  getModlist(modlistId: string): Observable<Modlist> {
    return this.http.get<Modlist>(`${this.baseUrl}/modlist/${modlistId}`);
  }

  // Downloads
  startDownloads(modlistId: string, modIds?: number[]): Observable<DownloadStatus[]> {
    return this.http.post<DownloadStatus[]>(`${this.baseUrl}/downloads/start`, {
      modlist_id: modlistId,
      mod_ids: modIds,
    });
  }

  getDownloadStatus(modlistId: string): Observable<DownloadStatus[]> {
    return this.http.get<DownloadStatus[]>(
      `${this.baseUrl}/downloads/${modlistId}/status`
    );
  }

  // Settings
  getSettings(): Observable<any> {
    return this.http.get(`${this.baseUrl}/settings/`);
  }

  updateSettings(settings: any): Observable<any> {
    return this.http.put(`${this.baseUrl}/settings/`, settings);
  }

  // Stats (public)
  getStats(): Observable<{ modlists_generated: number; games_supported: number }> {
    return this.http.get<{ modlists_generated: number; games_supported: number }>(
      `${this.baseUrl}/stats/`
    );
  }

  // Health
  healthCheck(): Observable<{ status: string; app: string }> {
    return this.http.get<{ status: string; app: string }>(`${this.baseUrl}/health`);
  }
}
