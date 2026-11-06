import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { Division, Inscripcion, Liga, Partido, Ranking } from '../../core/models';

@Component({selector: 'app-home', standalone: true, imports: [DatePipe, DecimalPipe, RouterLink], templateUrl: './home.component.html'})
export class HomeComponent implements OnInit {
  private readonly api = inject(ApiService);
  readonly liga = signal<Liga | null>(null);
  readonly divisiones = signal<Division[]>([]);
  readonly activa = signal<Division | null>(null);
  readonly ranking = signal<Ranking[]>([]);
  readonly partidos = signal<Partido[]>([]);
  readonly jugadores = signal<Inscripcion[]>([]);
  readonly cargando = signal(true);
  readonly cargandoPanel = signal(false);
  readonly error = signal('');
  readonly totalPartidos = computed(() => this.ranking().reduce((s, f) => s + f.partidos, 0) / 2);

  ngOnInit(): void {
    this.api.ligaPrincipal().subscribe({next: liga => {
      this.liga.set(liga);
      this.api.divisiones(liga.id).subscribe({next: divisiones => {
        this.divisiones.set(divisiones); this.cargando.set(false);
        if (divisiones.length) this.seleccionar(divisiones[0]);
      }, error: () => this.fallar()});
    }, error: () => this.fallar()});
  }

  seleccionar(division: Division): void {
    if (this.activa()?.id === division.id && this.ranking().length) return;
    this.activa.set(division); this.cargandoPanel.set(true); this.error.set('');
    this.api.panelDivision(division.id).subscribe({next: panel => {
      this.ranking.set(panel.ranking); this.partidos.set(panel.partidos); this.jugadores.set(panel.jugadores); this.cargandoPanel.set(false);
    }, error: () => {this.error.set('No pudimos cargar esta división. Intenta nuevamente.'); this.cargandoPanel.set(false);}});
  }

  iniciales(nombre: string): string { return nombre.split(' ').slice(0, 2).map(p => p[0]).join('').toUpperCase(); }
  puntajes(p: Partido, jugador: 'a'|'b'): string[] {
    return [p.set_1, p.set_2, p.super_tiebreak].filter(Boolean).map(set => {
      const partes = set.split(/\s*[\/-]\s*/);
      return jugador === 'a' ? partes[0] : partes[1];
    });
  }
  private fallar(): void { this.error.set('No hay una liga principal disponible o el servidor no responde.'); this.cargando.set(false); }
}
