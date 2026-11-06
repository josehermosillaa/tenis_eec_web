import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe, TitleCasePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { forkJoin, switchMap } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { Categoria, Division, Inscripcion, Jugador, Liga, Torneo, Usuario } from '../../core/models';

type Seccion = 'resumen'|'ligas'|'divisiones'|'jugadores'|'partidos'|'torneos';

@Component({selector: 'app-admin', standalone: true, imports: [FormsModule, DatePipe, TitleCasePipe, RouterLink], templateUrl: './admin.component.html'})
export class AdminComponent implements OnInit {
  private readonly api = inject(ApiService); private readonly router = inject(Router);
  readonly usuario = signal<Usuario|null>(null); readonly seccion = signal<Seccion>('resumen');
  readonly ligas = signal<Liga[]>([]); readonly categorias = signal<Categoria[]>([]); readonly divisiones = signal<Division[]>([]);
  readonly jugadores = signal<Jugador[]>([]); readonly torneos = signal<Torneo[]>([]); readonly inscripciones = signal<Inscripcion[]>([]);
  readonly ocupado = signal(false); readonly mensaje = signal(''); readonly error = signal('');
  ligaForm = {nombre:'', fecha_inicio:'', descripcion:'', estado:'ACTIVA'};
  categoriaNombre = '';
  divisionForm = {liga:0, nombre:'', orden:1, categorias:[] as number[]};
  jugadorForm = {nombre:'', categoria:0, estado:'ACTIVO', division:0};
  partidoForm = {division:0, fecha:new Date().toISOString().slice(0,10), jugador_a:0, jugador_b:0, set_1:'', set_2:'', super_tiebreak:''};
  torneoForm = {liga:0, nombre:'', fecha:new Date().toISOString().slice(0,10), descripcion:''};

  ngOnInit(): void { this.recargar(); }
  cambiar(seccion: Seccion): void { this.seccion.set(seccion); this.limpiarEstado(); }
  recargar(): void {
    this.ocupado.set(true);
    forkJoin({usuario:this.api.sesion(), ligas:this.api.ligasAdmin(), categorias:this.api.categoriasAdmin(), divisiones:this.api.divisionesAdmin(), jugadores:this.api.jugadoresAdmin(), torneos:this.api.torneosAdmin()}).subscribe({next:r=>{
      this.usuario.set(r.usuario); this.ligas.set(r.ligas); this.categorias.set(r.categorias); this.divisiones.set(r.divisiones); this.jugadores.set(r.jugadores); this.torneos.set(r.torneos);
      if (!this.divisionForm.liga && r.ligas[0]) this.divisionForm.liga=r.ligas[0].id;
      if (!this.jugadorForm.categoria && r.categorias[0]) this.jugadorForm.categoria=r.categorias[0].id;
      if (!this.torneoForm.liga && r.ligas[0]) this.torneoForm.liga=r.ligas[0].id;
      if (!this.partidoForm.division && r.divisiones[0]) {this.partidoForm.division=r.divisiones[0].id; this.cargarInscripciones();}
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
  guardarJugador(): void {
    const {division,...datos}=this.jugadorForm; const peticion=this.api.crearJugador(datos);
    this.ejecutar(division ? peticion.pipe(switchMap(j=>this.api.inscribir(division,j.id))) : peticion, division?'Jugador creado e inscrito.':'Jugador creado.',()=>{this.jugadorForm={nombre:'',categoria:this.categorias()[0]?.id||0,estado:'ACTIVO',division:0};this.recargar();});
  }
  cargarInscripciones(): void { if (!this.partidoForm.division) return; this.api.panelDivision(this.partidoForm.division).subscribe(r=>this.inscripciones.set(r.jugadores.filter(i=>i.activa))); }
  guardarPartido(): void { this.ejecutar(this.api.crearPartido(this.partidoForm), 'Resultado registrado y ranking actualizado.',()=>{this.partidoForm={...this.partidoForm,jugador_a:0,jugador_b:0,set_1:'',set_2:'',super_tiebreak:''};}); }
  guardarTorneo(): void { this.ejecutar(this.api.crearTorneo(this.torneoForm),'Torneo creado.',()=>{this.torneoForm={liga:this.ligas()[0]?.id||0,nombre:'',fecha:new Date().toISOString().slice(0,10),descripcion:''};this.recargar();}); }
  salir(): void { this.api.logout().subscribe({next:()=>this.router.navigateByUrl('/')}); }
  ligaNombre(id:number):string { return this.ligas().find(l=>l.id===id)?.nombre||'—'; }
  divisionNombre(id:number):string { return this.divisiones().find(d=>d.id===id)?.nombre||'—'; }
  private ejecutar(obs:any, mensaje:string, terminado:()=>void):void { this.limpiarEstado();this.ocupado.set(true);obs.subscribe({next:()=>{this.mensaje.set(mensaje);this.ocupado.set(false);terminado();},error:(e:any)=>{const data=e?.error;this.error.set(typeof data==='string'?data:(data?.detail||Object.values(data||{}).flat().join(' ')||'No fue posible guardar los cambios.'));this.ocupado.set(false);}}); }
  private limpiarEstado():void {this.mensaje.set('');this.error.set('');}
}
