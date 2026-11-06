import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { forkJoin, Observable, switchMap } from 'rxjs';
import { Categoria, Division, Inscripcion, Jugador, Liga, Partido, Ranking, Torneo, Usuario } from './models';

@Injectable({providedIn: 'root'})
export class ApiService {
  private readonly http = inject(HttpClient);
  ligaPrincipal(): Observable<Liga> { return this.http.get<Liga>('/api/ligas/principal/'); }
  divisiones(ligaId: number): Observable<Division[]> { return this.http.get<Division[]>(`/api/ligas/${ligaId}/divisiones/`); }
  panelDivision(id: number): Observable<{ranking: Ranking[]; partidos: Partido[]; jugadores: Inscripcion[]}> {
    return forkJoin({ranking: this.http.get<Ranking[]>(`/api/divisiones/${id}/ranking/`), partidos: this.http.get<Partido[]>(`/api/divisiones/${id}/partidos/`), jugadores: this.http.get<Inscripcion[]>(`/api/divisiones/${id}/jugadores/`)});
  }
  login(username: string, password: string): Observable<unknown> {
    return this.http.get('/api/auth/csrf/').pipe(switchMap(() => this.http.post('/api/auth/login/', {username, password})), switchMap(() => this.http.get('/api/auth/csrf/')));
  }
  sesion(): Observable<Usuario> { return this.http.get<Usuario>('/api/auth/me/'); }
  logout(): Observable<void> { return this.http.post<void>('/api/auth/logout/', {}); }
  ligasAdmin(): Observable<Liga[]> { return this.http.get<Liga[]>('/api/admin/ligas/'); }
  categoriasAdmin(): Observable<Categoria[]> { return this.http.get<Categoria[]>('/api/admin/categorias/'); }
  divisionesAdmin(): Observable<Division[]> { return this.http.get<Division[]>('/api/admin/divisiones/'); }
  jugadoresAdmin(): Observable<Jugador[]> { return this.http.get<Jugador[]>('/api/admin/jugadores/'); }
  torneosAdmin(): Observable<Torneo[]> { return this.http.get<Torneo[]>('/api/admin/torneos/'); }
  crearLiga(data: object): Observable<Liga> { return this.http.post<Liga>('/api/admin/ligas/', data); }
  hacerPrincipal(id: number): Observable<Liga> { return this.http.post<Liga>(`/api/admin/ligas/${id}/principal/`, {}); }
  cerrarLiga(id: number): Observable<unknown> { return this.http.post(`/api/admin/ligas/${id}/cerrar/`, {}); }
  crearCategoria(nombre: string): Observable<Categoria> { return this.http.post<Categoria>('/api/admin/categorias/', {nombre}); }
  crearDivision(data: object): Observable<Division> { return this.http.post<Division>('/api/admin/divisiones/', data); }
  configurarCategorias(id: number, categorias: number[]): Observable<Division> { return this.http.put<Division>(`/api/admin/divisiones/${id}/categorias/`, {categorias}); }
  crearJugador(data: object): Observable<Jugador> { return this.http.post<Jugador>('/api/admin/jugadores/', data); }
  inscribir(division: number, jugador: number): Observable<Inscripcion> { return this.http.post<Inscripcion>(`/api/admin/divisiones/${division}/inscripciones/`, {jugador}); }
  crearPartido(data: object): Observable<Partido> { return this.http.post<Partido>('/api/admin/partidos/', data); }
  crearTorneo(data: object): Observable<Torneo> { return this.http.post<Torneo>('/api/admin/torneos/', data); }
}
