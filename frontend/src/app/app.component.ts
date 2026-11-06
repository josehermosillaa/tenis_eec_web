import { Component, inject } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterOutlet } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs';
import { ApiService } from './core/api.service';

@Component({selector: 'app-root', standalone: true, imports: [RouterLink, RouterOutlet], template: `
  @if (!esAdmin()) {
  <header class="site-header">
    <nav class="container-xl nav-shell" aria-label="Navegación principal">
      <a routerLink="/" class="brand"><img src="/logo-estadio-espanol.png" alt="Tenis Estadio Español Curicó"><span><b>Tenis EEC</b><small>Ranking oficial</small></span></a>
      <div class="header-actions">
        <a [routerLink]="api.autenticado() ? '/admin' : '/login'" class="admin-link"><span aria-hidden="true">⚙</span> Administración</a>
        @if (api.autenticado()) {
          <button type="button" class="logout-link" (click)="cerrarSesion()"><span aria-hidden="true">↪</span> Cerrar sesión</button>
        }
      </div>
    </nav>
  </header>
  }
  <main><router-outlet /></main>
  @if (!esAdmin()) {
  <footer><div class="container-xl">Tenis EEC · Competencia, comunidad y juego limpio</div></footer>
  }
`})
export class AppComponent {
  private readonly router = inject(Router);
  readonly api = inject(ApiService);
  readonly esAdmin = toSignal(this.router.events.pipe(
    filter((event): event is NavigationEnd => event instanceof NavigationEnd),
    map(event => event.urlAfterRedirects.startsWith('/admin'))
  ), {initialValue: this.router.url.startsWith('/admin')});

  constructor() {
    this.api.sesion().subscribe({error: () => this.api.autenticado.set(false)});
  }

  cerrarSesion(): void {
    this.api.logout().subscribe({next: () => this.router.navigateByUrl('/')});
  }
}
