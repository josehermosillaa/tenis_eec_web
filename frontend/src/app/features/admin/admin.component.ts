import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe, TitleCasePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { forkJoin, switchMap } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { Categoria, Division, Inscripcion, InscripcionActiva, Jugador, Liga, Partido, Torneo, Usuario } from '../../core/models';

type Seccion = 'resumen'|'ligas'|'divisiones'|'jugadores'|'partidos'|'torneos';

@Component({selector: 'app-admin', standalone: true, imports: [FormsModule, DatePipe, TitleCasePipe, RouterLink], templateUrl: './admin.component.html'})
export class AdminComponent implements OnInit {
  private readonly api = inject(ApiService); private readonly router = inject(Router);
  readonly usuario = signal<Usuario|null>(null); readonly seccion = signal<Seccion>('resumen');
  readonly ligas = signal<Liga[]>([]); readonly categorias = signal<Categoria[]>([]); readonly divisiones = signal<Division[]>([]);
  readonly ligaActiva = computed(() => this.ligas().find(l => l.es_principal && l.estado === 'ACTIVA') ?? null);
  readonly divisionesLigaActiva = computed(() => {
    const liga = this.ligaActiva();
    return liga ? this.divisiones().filter(d => d.liga === liga.id && d.estado === 'ACTIVA') : [];
  });
  readonly partidos = signal<Partido[]>([]);
  readonly partidosLigaActiva = computed(() => {
    const divisiones = new Set(this.divisionesLigaActiva().map(d => d.id));
    return this.partidos().filter(p => p.estado === 'TERMINADO' && divisiones.has(p.division));
  });
  readonly divisionPartidosSeleccionada = signal(0);
  readonly divisionesConPartidos = computed(() => {
    const conPartidos = new Set(this.partidosLigaActiva().map(p => p.division));
    return this.divisionesLigaActiva().filter(d => conPartidos.has(d.id));
  });
  readonly partidosDivisionSeleccionada = computed(() =>
    this.partidosLigaActiva().filter(p => p.division === this.divisionPartidosSeleccionada())
  );
  readonly jugadores = signal<Jugador[]>([]); readonly torneos = signal<Torneo[]>([]); readonly inscripciones = signal<Inscripcion[]>([]);
  readonly busquedaListadoJugadores = signal('');
  readonly jugadoresFiltrados = computed(() => {
    const termino = this.normalizarBusqueda(this.busquedaListadoJugadores());
    return termino
      ? this.jugadores().filter(j => this.normalizarBusqueda(j.nombre).includes(termino))
      : this.jugadores();
  });
  readonly busquedaInscripcion = signal(''); readonly jugadorSeleccionado = signal<Jugador|null>(null);
  readonly sugerenciasJugadores = computed(() => {
    const termino = this.normalizarBusqueda(this.busquedaInscripcion());
    if (termino.length < 2 || this.jugadorSeleccionado()) return [];
    return this.jugadores().filter(j => j.estado === 'ACTIVO' && this.normalizarBusqueda(j.nombre).includes(termino)).slice(0, 8);
  });
  readonly busquedaJugadorA = signal(''); readonly busquedaJugadorB = signal('');
  private readonly participantesVersion = signal(0);
  readonly sugerenciasJugadorA = computed(() => this.buscarInscripciones(this.busquedaJugadorA(), this.partidoForm.jugador_a, this.partidoForm.jugador_b));
  readonly sugerenciasJugadorB = computed(() => this.buscarInscripciones(this.busquedaJugadorB(), this.partidoForm.jugador_b, this.partidoForm.jugador_a));
  readonly ocupado = signal(false); readonly mensaje = signal(''); readonly error = signal('');
  readonly jugadorEditando = signal<number|null>(null);
  readonly divisionEditando = signal<number|null>(null);
  readonly partidoEditando = signal<number|null>(null);
  ligaForm = {nombre:'', fecha_inicio:'', descripcion:'', estado:'ACTIVA'};
  categoriaNombre = '';
  divisionForm = {liga:0, nombre:'', orden:1, categorias:[] as number[]};
  divisionEdicion = {nombre:'', orden:1, categorias:[] as number[]};
  jugadorForm = {nombre:'', categoria:0, estado:'ACTIVO', division:0};
  jugadorEdicion = {nombre:'', categoria:0};
  inscripcionDivision = 0;
  partidoForm = {division:0, fecha:new Date().toISOString().slice(0,10), jugador_a:0, jugador_b:0, set_1:'', set_2:'', super_tiebreak:''};
  torneoForm = {liga:0, nombre:'', fecha:new Date().toISOString().slice(0,10), descripcion:''};

  ngOnInit(): void { this.recargar(); }
  cambiar(seccion: Seccion): void { this.seccion.set(seccion); this.limpiarEstado(); }
  recargar(): void {
    this.ocupado.set(true);
    forkJoin({usuario:this.api.sesion(), ligas:this.api.ligasAdmin(), categorias:this.api.categoriasAdmin(), divisiones:this.api.divisionesAdmin(), jugadores:this.api.jugadoresAdmin(), partidos:this.api.partidosAdmin(), torneos:this.api.torneosAdmin()}).subscribe({next:r=>{
      this.usuario.set(r.usuario); this.ligas.set(r.ligas); this.categorias.set(r.categorias); this.divisiones.set(r.divisiones); this.jugadores.set(r.jugadores); this.partidos.set(r.partidos); this.torneos.set(r.torneos);
      if (!this.divisionesConPartidos().some(d => d.id === this.divisionPartidosSeleccionada())) {
        this.divisionPartidosSeleccionada.set(this.divisionesConPartidos()[0]?.id || 0);
      }
      if (!this.divisionesLigaActiva().some(d => d.id === this.jugadorForm.division)) this.jugadorForm.division=0;
      if (!this.divisionesLigaActiva().some(d => d.id === this.inscripcionDivision)) this.inscripcionDivision=0;
      if (!this.divisionForm.liga && r.ligas[0]) this.divisionForm.liga=r.ligas[0].id;
      if (!this.jugadorForm.categoria && r.categorias[0]) this.jugadorForm.categoria=r.categorias[0].id;
      if (!this.torneoForm.liga && r.ligas[0]) this.torneoForm.liga=r.ligas[0].id;
      if (!this.divisionesLigaActiva().some(d => d.id === this.partidoForm.division)) {
        this.partidoForm.division=this.divisionesLigaActiva()[0]?.id||0; this.cargarInscripciones();
      }
      this.ocupado.set(false);
    },error:()=>{this.error.set('No fue posible cargar el panel.');this.ocupado.set(false);}});
  }
  guardarLiga(): void { this.ejecutar(this.api.crearLiga(this.ligaForm), 'Liga creada correctamente.', () => {this.ligaForm={nombre:'',fecha_inicio:'',descripcion:'',estado:'ACTIVA'};this.recargar();}); }
  principal(liga: Liga): void { this.ejecutar(this.api.hacerPrincipal(liga.id), 'Liga principal actualizada.', () => this.recargar()); }
  cerrar(liga: Liga): void { if (!confirm(`¿Cerrar ${liga.nombre}? Se guardarán las clasificaciones finales.`)) return; this.ejecutar(this.api.cerrarLiga(liga.id), 'Liga cerrada y snapshots guardados.', () => this.recargar()); }
  guardarCategoria(): void { this.ejecutar(this.api.crearCategoria(this.categoriaNombre), 'Categoría creada.', () => {this.categoriaNombre='';this.recargar();}); }
  alternarCategoria(id: number, checked: boolean): void { this.divisionForm.categorias = checked ? [...this.divisionForm.categorias,id] : this.divisionForm.categorias.filter(x=>x!==id); }
  guardarDivision(): void {
    const {categorias,...datos}=this.divisionForm;
    this.ejecutar(this.api.crearDivision(datos).pipe(switchMap(d=>this.api.configurarCategorias(d.id,categorias))), 'División creada y configurada.', () => {this.divisionForm={liga:this.ligas()[0]?.id||0,nombre:'',orden:1,categorias:[]};this.recargar();});
  }
  eliminarDivision(division: Division): void {
    if (!confirm(`¿Eliminar la división ${division.nombre}? Esta acción no se puede deshacer.`)) return;
    this.ejecutar(this.api.eliminarDivision(division.id), 'División eliminada correctamente.', () => this.recargar());
  }
  cancelarDivision(division: Division): void {
    if (!confirm(`¿Cancelar la división ${division.nombre}? Se ocultará del sitio público y no admitirá nuevas inscripciones ni partidos.`)) return;
    this.ejecutar(this.api.cancelarDivision(division.id),'División cancelada. Su historial se conserva.',()=>this.recargar());
  }
  reactivarDivision(division: Division): void {
    this.ejecutar(this.api.reactivarDivision(division.id),'División reactivada correctamente.',()=>this.recargar());
  }
  editarDivision(division: Division): void {
    this.divisionEditando.set(division.id);
    this.divisionEdicion={nombre:division.nombre,orden:division.orden,categorias:division.categorias.map(c=>c.id)};
    this.limpiarEstado();
  }
  cancelarEdicionDivision(): void { this.divisionEditando.set(null); }
  alternarCategoriaEdicion(id: number, checked: boolean): void {
    this.divisionEdicion.categorias=checked?[...this.divisionEdicion.categorias,id]:this.divisionEdicion.categorias.filter(x=>x!==id);
  }
  guardarEdicionDivision(division: Division): void {
    this.ejecutar(this.api.actualizarDivision(division.id,this.divisionEdicion),'División actualizada y ordenada correctamente.',()=>{this.divisionEditando.set(null);this.recargar();});
  }
  guardarJugador(): void {
    const {division,...datos}=this.jugadorForm; const peticion=this.api.crearJugador(datos);
    this.ejecutar(division ? peticion.pipe(switchMap(j=>this.api.inscribir(division,j.id))) : peticion, division?'Jugador creado e inscrito.':'Jugador creado.',()=>{this.jugadorForm={nombre:'',categoria:this.categorias()[0]?.id||0,estado:'ACTIVO',division:0};this.recargar();});
  }
  cambiarCategoriaJugador(categoria: number): void {
    this.jugadorForm.categoria = categoria;
    if (!this.divisionesCompatibles(categoria).some(d => d.id === this.jugadorForm.division)) {
      this.jugadorForm.division = 0;
    }
  }
  divisionesCompatibles(categoria: number): Division[] {
    return this.divisionesLigaActiva().filter(d => d.categorias.some(c => c.id === categoria));
  }
  cambiarEstadoJugador(jugador: Jugador): void {
    const nuevoEstado = jugador.estado === 'ACTIVO' ? 'RETIRADO' : 'ACTIVO';
    const accion = nuevoEstado === 'RETIRADO' ? 'retirar' : 'reactivar';
    if (!confirm(`¿Quieres ${accion} a ${jugador.nombre}? Sus partidos históricos se conservarán.`)) return;
    this.ejecutar(this.api.actualizarJugador(jugador.id, {estado:nuevoEstado}),
      nuevoEstado === 'RETIRADO' ? 'Jugador retirado del ranking.' : 'Jugador reactivado en el ranking.', () => this.recargar());
  }
  editarJugador(jugador: Jugador): void {
    this.jugadorEditando.set(jugador.id);
    this.jugadorEdicion = {nombre: jugador.nombre, categoria: jugador.categoria};
    this.limpiarEstado();
  }
  cancelarEdicionJugador(): void {
    this.jugadorEditando.set(null);
  }
  guardarEdicionJugador(jugador: Jugador): void {
    const nombre = this.jugadorEdicion.nombre.trim();
    if (!nombre || !this.jugadorEdicion.categoria) return;
    this.ejecutar(
      this.api.actualizarJugador(jugador.id, {nombre, categoria: this.jugadorEdicion.categoria}),
      'Jugador actualizado correctamente.',
      () => { this.jugadorEditando.set(null); this.recargar(); }
    );
  }
  quitarDeDivision(inscripcion: InscripcionActiva, jugador: Jugador): void {
    if (!confirm(`¿Quitar a ${jugador.nombre} de ${inscripcion.division_nombre}? Sus partidos y resultados se conservarán.`)) return;
    this.ejecutar(
      this.api.quitarInscripcion(inscripcion.id),
      `Jugador quitado de ${inscripcion.division_nombre}.`,
      () => this.recargar()
    );
  }
  buscarJugador(valor: string): void {
    this.busquedaInscripcion.set(valor);
    if (this.jugadorSeleccionado()?.nombre !== valor) this.jugadorSeleccionado.set(null);
  }
  seleccionarJugador(jugador: Jugador): void {
    this.jugadorSeleccionado.set(jugador); this.busquedaInscripcion.set(jugador.nombre); this.inscripcionDivision=0;
  }
  inscribirExistente(): void {
    const jugador = this.jugadorSeleccionado();
    if (!jugador || !this.inscripcionDivision) return;
    this.ejecutar(this.api.inscribir(this.inscripcionDivision, jugador.id), 'Jugador inscrito en la división.', () => {
      this.busquedaInscripcion.set(''); this.jugadorSeleccionado.set(null); this.inscripcionDivision=0; this.recargar();
    });
  }
  cargarInscripciones(): void {
    this.partidoForm.jugador_a=0; this.partidoForm.jugador_b=0; this.busquedaJugadorA.set(''); this.busquedaJugadorB.set('');
    if (!this.partidoForm.division) return;
    this.api.panelDivision(this.partidoForm.division).subscribe(r=>this.inscripciones.set(r.jugadores.filter(i=>i.activa&&i.jugador_detalle.estado==='ACTIVO')));
  }
  buscarParticipante(lado: 'a'|'b', valor: string): void {
    if (lado==='a') { this.busquedaJugadorA.set(valor); this.partidoForm.jugador_a=0; }
    else { this.busquedaJugadorB.set(valor); this.partidoForm.jugador_b=0; }
  }
  seleccionarParticipante(lado: 'a'|'b', inscripcion: Inscripcion): void {
    if (lado==='a') { this.partidoForm.jugador_a=inscripcion.id; this.busquedaJugadorA.set(inscripcion.jugador_detalle.nombre); }
    else { this.partidoForm.jugador_b=inscripcion.id; this.busquedaJugadorB.set(inscripcion.jugador_detalle.nombre); }
    this.participantesVersion.update(version => version + 1);
  }
  guardarPartido(): void {
    const id = this.partidoEditando();
    const division = this.partidoForm.division;
    const peticion = id ? this.api.actualizarPartido(id, this.partidoForm) : this.api.crearPartido(this.partidoForm);
    this.ejecutar(peticion, id ? 'Partido actualizado y ranking recalculado.' : 'Resultado registrado y ranking actualizado.',()=>{this.cancelarEdicionPartido();this.divisionPartidosSeleccionada.set(division);this.recargar();});
  }
  editarPartido(partido: Partido): void {
    this.divisionPartidosSeleccionada.set(partido.division);
    this.partidoEditando.set(partido.id);
    this.partidoForm = {division:partido.division, fecha:partido.fecha, jugador_a:partido.jugador_a, jugador_b:partido.jugador_b, set_1:partido.set_1, set_2:partido.set_2, super_tiebreak:partido.super_tiebreak};
    this.busquedaJugadorA.set(partido.jugador_a_nombre); this.busquedaJugadorB.set(partido.jugador_b_nombre); this.limpiarEstado();
    this.api.panelDivision(partido.division).subscribe(r=>this.inscripciones.set(r.jugadores.filter(i=>i.activa||i.id===partido.jugador_a||i.id===partido.jugador_b)));
  }
  cancelarEdicionPartido(): void {
    this.partidoEditando.set(null);
    this.partidoForm={division:this.divisionesLigaActiva()[0]?.id||0,fecha:new Date().toISOString().slice(0,10),jugador_a:0,jugador_b:0,set_1:'',set_2:'',super_tiebreak:''};
    this.busquedaJugadorA.set('');this.busquedaJugadorB.set('');
    if (this.partidoForm.division) this.cargarInscripciones();
  }
  eliminarPartido(partido: Partido): void {
    if (!confirm(`¿Eliminar el partido entre ${partido.jugador_a_nombre} y ${partido.jugador_b_nombre}? Dejará de contar en el ranking.`)) return;
    this.ejecutar(this.api.actualizarPartido(partido.id,{estado:'ANULADO'}),'Partido eliminado y ranking actualizado.',()=>{if(this.partidoEditando()===partido.id)this.cancelarEdicionPartido();this.recargar();});
  }
  seleccionarDivisionPartidos(division: number): void {
    this.divisionPartidosSeleccionada.set(division);
  }
  guardarTorneo(): void { this.ejecutar(this.api.crearTorneo(this.torneoForm),'Torneo creado.',()=>{this.torneoForm={liga:this.ligas()[0]?.id||0,nombre:'',fecha:new Date().toISOString().slice(0,10),descripcion:''};this.recargar();}); }
  salir(): void { this.api.logout().subscribe({next:()=>this.router.navigateByUrl('/')}); }
  ligaNombre(id:number):string { return this.ligas().find(l=>l.id===id)?.nombre||'—'; }
  divisionNombre(id:number):string { return this.divisiones().find(d=>d.id===id)?.nombre||'—'; }
  private ejecutar(obs:any, mensaje:string, terminado:()=>void):void { this.limpiarEstado();this.ocupado.set(true);obs.subscribe({next:()=>{this.mensaje.set(mensaje);this.ocupado.set(false);terminado();},error:(e:any)=>{this.error.set(this.mensajeError(e?.error));this.ocupado.set(false);}}); }
  private mensajeError(data: any): string {
    if (typeof data === 'string') {
      const texto = data.trim();
      return /<!doctype|<html/i.test(texto) ? 'El servidor no pudo procesar la solicitud. Revisa los datos e inténtalo nuevamente.' : texto;
    }
    if (data?.detail) return Array.isArray(data.detail) ? data.detail.join(' ') : String(data.detail);
    const mensajes = Object.values(data || {}).flat(2).filter(Boolean).map(String);
    return mensajes.join(' ') || 'No fue posible guardar los cambios.';
  }
  private normalizarBusqueda(valor: string): string {
    return valor.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('es-CL').trim().replace(/\s+/g, ' ');
  }
  private buscarInscripciones(valor: string, seleccionado: number, excluir: number): Inscripcion[] {
    this.participantesVersion();
    const termino = this.normalizarBusqueda(valor);
    if (termino.length < 2 || seleccionado) return [];
    return this.inscripciones().filter(i => i.id !== excluir && this.normalizarBusqueda(i.jugador_detalle.nombre).includes(termino)).slice(0, 8);
  }
  private limpiarEstado():void {this.mensaje.set('');this.error.set('');}
}
