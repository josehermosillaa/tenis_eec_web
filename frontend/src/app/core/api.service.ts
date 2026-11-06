import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { forkJoin, Observable, switchMap, tap } from 'rxjs';
import { Categoria, Division, Inscripcion, Jugador, Liga, Partido, PerfilJugador, Ranking, Torneo, Usuario } from './models';

@Injectable({providedIn: 'root'})
export class ApiService {
  private readonly http = inject(HttpClient);
  readonly autenticado = signal(false);
  ligaPrincipal(): Observable<Liga> { return this.http.get<Liga>('/api/ligas/principal/'); }
  divisiones(ligaId: number): Observable<Division[]> { return this.http.get<Division[]>(`/api/ligas/${ligaId}/divisiones/`); }
  panelDivision(id: number): Observable<{ranking: Ranking[]; partidos: Partido[]; jugadores: Inscripcion[]}> {
    return forkJoin({ranking: this.http.get<Ranking[]>(`/api/divisiones/${id}/ranking/`), partidos: this.http.get<Partido[]>(`/api/divisiones/${id}/partidos/`), jugadores: this.http.get<Inscripcion[]>(`/api/divisiones/${id}/jugadores/`)});
  }
  perfilJugador(id: number): Observable<PerfilJugador> { return this.http.get<PerfilJugador>(`/api/jugadores/${id}/perfil/`); }
  login(username: string, password: string): Observable<unknown> {
    return this.http.get<{csrfToken: string}>('/api/auth/csrf/').pipe(
      switchMap(({csrfToken}) => this.http.post('/api/auth/login/', {username, password}, {
        headers: {'X-CSRFToken': csrfToken}
      })),
      tap(() => this.autenticado.set(true))
    );
  }
  sesion(): Observable<Usuario> { return this.http.get<Usuario>('/api/auth/me/').pipe(tap(() => this.autenticado.set(true))); }
  logout(): Observable<void> { return this.http.post<void>('/api/auth/logout/', {}).pipe(tap(() => this.autenticado.set(false))); }
  ligasAdmin(): Observable<Liga[]> { return this.http.get<Liga[]>('/api/admin/ligas/'); }
  categoriasAdmin(): Observable<Categoria[]> { return this.http.get<Categoria[]>('/api/admin/categorias/'); }
  divisionesAdmin(): Observable<Division[]> { return this.http.get<Division[]>('/api/admin/divisiones/'); }
  jugadoresAdmin(): Observable<Jugador[]> { return this.http.get<Jugador[]>('/api/admin/jugadores/'); }
  partidosAdmin(): Observable<Partido[]> { return this.http.get<Partido[]>('/api/admin/partidos/'); }
  torneosAdmin(): Observable<Torneo[]> { return this.http.get<Torneo[]>('/api/admin/torneos/'); }
  crearLiga(data: object): Observable<Liga> { return this.http.post<Liga>('/api/admin/ligas/', data); }
  hacerPrincipal(id: number): Observable<Liga> { return this.http.post<Liga>(`/api/admin/ligas/${id}/principal/`, {}); }
  cerrarLiga(id: number): Observable<unknown> { return this.http.post(`/api/admin/ligas/${id}/cerrar/`, {}); }
  crearCategoria(nombre: string): Observable<Categoria> { return this.http.post<Categoria>('/api/admin/categorias/', {nombre}); }
  crearDivision(data: object): Observable<Division> { return this.http.post<Division>('/api/admin/divisiones/', data); }
  configurarCategorias(id: number, categorias: number[]): Observable<Division> { return this.http.put<Division>(`/api/admin/divisiones/${id}/categorias/`, {categorias}); }
  actualizarDivision(id: number, data: object): Observable<Division> { return this.http.patch<Division>(`/api/admin/divisiones/${id}/`, data); }
  eliminarDivision(id: number): Observable<void> { return this.http.delete<void>(`/api/admin/divisiones/${id}/`); }
  cancelarDivision(id: number): Observable<Division> { return this.http.post<Division>(`/api/admin/divisiones/${id}/cancelar/`, {}); }
  reactivarDivision(id: number): Observable<Division> { return this.http.post<Division>(`/api/admin/divisiones/${id}/reactivar/`, {}); }
  crearJugador(data: object): Observable<Jugador> { return this.http.post<Jugador>('/api/admin/jugadores/', data); }
  actualizarJugador(id: number, data: object): Observable<Jugador> { return this.http.patch<Jugador>(`/api/admin/jugadores/${id}/`, data); }
  inscribir(division: number, jugador: number): Observable<Inscripcion> { return this.http.post<Inscripcion>(`/api/admin/divisiones/${division}/inscripciones/`, {jugador}); }
  quitarInscripcion(id: number): Observable<{id: number; activa: boolean}> { return this.http.patch<{id: number; activa: boolean}>(`/api/admin/inscripciones/${id}/`, {activa:false}); }
  crearPartido(data: object): Observable<Partido> { return this.http.post<Partido>('/api/admin/partidos/', data); }
  actualizarPartido(id: number, data: object): Observable<Partido> { return this.http.patch<Partido>(`/api/admin/partidos/${id}/`, data); }
  crearTorneo(data: object): Observable<Torneo> { return this.http.post<Torneo>('/api/admin/torneos/', data); }
}
