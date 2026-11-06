import { Component, inject } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterOutlet } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs';

@Component({selector: 'app-root', standalone: true, imports: [RouterLink, RouterOutlet], template: `
  @if (!esAdmin()) {
  <header class="site-header">
    <nav class="container-xl nav-shell" aria-label="Navegación principal">
      <a routerLink="/" class="brand"><span class="brand-ball">●</span><span><b>Tenis EEC</b><small>Ranking oficial</small></span></a>
      <a routerLink="/login" class="admin-link"><span aria-hidden="true">⚙</span> Administración</a>
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
  readonly esAdmin = toSignal(this.router.events.pipe(
    filter((event): event is NavigationEnd => event instanceof NavigationEnd),
    map(event => event.urlAfterRedirects.startsWith('/admin'))
  ), {initialValue: this.router.url.startsWith('/admin')});
}
