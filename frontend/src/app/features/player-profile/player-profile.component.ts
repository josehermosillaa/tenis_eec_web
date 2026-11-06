import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { PerfilJugador } from '../../core/models';

@Component({
  selector: 'app-player-profile', standalone: true, imports: [DatePipe, RouterLink],
  templateUrl: './player-profile.component.html'
})
export class PlayerProfileComponent implements OnInit {
  private readonly api = inject(ApiService); private readonly route = inject(ActivatedRoute);
  readonly perfil = signal<PerfilJugador|null>(null); readonly cargando = signal(true); readonly error = signal('');
  readonly tarjetaAbierta = signal(false); readonly generando = signal(false);
  readonly porcentajeVictorias = computed(() => {
    const e = this.perfil()?.estadisticas; return e?.partidos ? Math.round(e.ganados * 100 / e.partidos) : 0;
  });
  readonly estiloGrafico = computed(() => `conic-gradient(#f20d18 0 ${this.porcentajeVictorias()}%, #343a40 ${this.porcentajeVictorias()}% 100%)`);

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.api.perfilJugador(id).subscribe({next:p=>{this.perfil.set(p);this.cargando.set(false);},error:()=>{this.error.set('No pudimos cargar este perfil.');this.cargando.set(false);}});
  }
  iniciales(nombre: string): string { return nombre.split(/\s+/).slice(0,2).map(p=>p[0]).join('').toUpperCase(); }
  marcador(p: {set_1:string;set_2:string;super_tiebreak:string}): string { return [p.set_1,p.set_2,p.super_tiebreak].filter(Boolean).join(' · '); }

  async descargar(): Promise<void> {
    this.generando.set(true); const blob = await this.crearTarjeta(); this.generando.set(false);
    const enlace=document.createElement('a'); enlace.href=URL.createObjectURL(blob); enlace.download=`rendimiento-${this.perfil()!.jugador.nombre.toLowerCase().replace(/\s+/g,'-')}.png`; enlace.click();
    setTimeout(()=>URL.revokeObjectURL(enlace.href),1000);
  }
  async compartir(): Promise<void> {
    this.generando.set(true); const blob=await this.crearTarjeta(); this.generando.set(false);
    const archivo=new File([blob],'rendimiento-tenis.png',{type:'image/png'});
    if (navigator.share && (!navigator.canShare || navigator.canShare({files:[archivo]}))) {
      await navigator.share({title:`Rendimiento de ${this.perfil()!.jugador.nombre}`,text:'Mi rendimiento en Tenis EEC',files:[archivo]});
    } else { await this.descargar(); }
  }
  private async crearTarjeta(): Promise<Blob> {
    const p=this.perfil()!, e=p.estadisticas!; const canvas=document.createElement('canvas'); canvas.width=1080; canvas.height=1920; const c=canvas.getContext('2d')!;
    const grad=c.createLinearGradient(0,0,1080,1920); grad.addColorStop(0,'#15191d');grad.addColorStop(.58,'#090b0e');grad.addColorStop(1,'#030405');c.fillStyle=grad;c.fillRect(0,0,1080,1920);
    c.fillStyle='rgba(255,255,255,.045)';c.beginPath();c.moveTo(610,0);c.lineTo(1080,0);c.lineTo(620,1920);c.lineTo(160,1920);c.closePath();c.fill();
    const centro=(texto:string,y:number,tamano:number,peso='700',color='#fff')=>{c.fillStyle=color;c.font=`${peso} ${tamano}px Arial`;c.textAlign='center';c.fillText(texto,540,y);};
    c.textAlign='left';c.fillStyle='#c4c9ce';c.font='700 30px Arial';c.fillText('TENIS EEC · RANKING OFICIAL',70,92);
    const logo=new Image();logo.src='/logo-estadio-espanol.png';await logo.decode();c.drawImage(logo,850,35,150,150);
    c.strokeStyle='#f20d18';c.lineWidth=7;c.beginPath();c.arc(540,330,128,0,Math.PI*2);c.stroke();centro(this.iniciales(p.jugador.nombre),365,108,'800');
    centro(p.jugador.nombre,535,58,'800');centro(p.division!.nombre.toUpperCase(),590,27,'800','#f20d18');centro(p.liga!.nombre,642,25,'400','#c4c9ce');
    const stats=[['#'+e.posicion,'POS.'],[String(e.partidos),'PJ'],[String(e.ganados),'V'],[String(e.perdidos),'D'],[String(e.puntos_totales),'PTS']];
    stats.forEach(([valor,label],i)=>{const x=70+i*190;c.fillStyle='rgba(255,255,255,.09)';c.roundRect(x,705,170,130,18);c.fill();c.textAlign='center';c.fillStyle='#fff';c.font='800 42px Arial';c.fillText(valor,x+85,760);c.fillStyle='#aebfd1';c.font='700 20px Arial';c.fillText(label,x+85,800);});
    centro('ÚLTIMOS PARTIDOS',935,24,'700','#b8c9dd');
    p.partidos.slice(0,5).forEach((m,i)=>{const y=980+i*135;c.fillStyle=m.ganado?'rgba(242,13,24,.16)':'rgba(100,108,116,.18)';c.roundRect(70,y,940,108,18);c.fill();c.fillStyle=m.ganado?'#f20d18':'#7b838a';c.beginPath();c.arc(112,y+54,27,0,Math.PI*2);c.fill();c.fillStyle='#fff';c.font='800 23px Arial';c.textAlign='center';c.fillText(m.ganado?'V':'D',112,y+62);c.textAlign='left';c.fillStyle='#fff';c.font='700 27px Arial';c.fillText(`vs ${m.rival}`,158,y+43);c.fillStyle='#c4c9ce';c.font='22px Arial';c.fillText(this.marcador(m),158,y+78);});
    centro(`${this.porcentajeVictorias()}% de victorias`,1740,34,'800','#f20d18');centro('Competencia · Comunidad · Juego limpio',1810,24,'400','#aab0b6');
    return await new Promise(resolve=>canvas.toBlob(blob=>resolve(blob!),'image/png'));
  }
}
