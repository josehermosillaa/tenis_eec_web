import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';

@Component({selector: 'app-login', standalone: true, imports: [FormsModule, RouterLink], template: `
<section class="login-page"><div class="login-card"><a routerLink="/" class="back">← Volver al ranking</a><img class="login-logo" src="/logo-estadio-espanol.png" alt="Tenis Estadio Español Curicó"><p class="eyebrow dark">Acceso privado</p><h1>Administración</h1><p>Ingresa con tu cuenta de administrador para gestionar la competencia.</p>
<form (ngSubmit)="entrar()"><label>Usuario<input name="username" [(ngModel)]="username" autocomplete="username" required></label><label>Contraseña<input name="password" [(ngModel)]="password" type="password" autocomplete="current-password" required></label>
@if (error()) {<div class="form-error">{{ error() }}</div>}<button [disabled]="enviando()">{{ enviando() ? 'Ingresando…' : 'Ingresar' }}</button></form></div></section>`})
export class LoginComponent {
  private readonly api = inject(ApiService); private readonly router = inject(Router);
  username = ''; password = ''; readonly enviando = signal(false); readonly error = signal('');
  entrar(): void {
    if (!this.username || !this.password) return;
    this.enviando.set(true); this.error.set('');
    this.api.login(this.username, this.password).subscribe({
      next: () => this.router.navigateByUrl('/admin'),
      error: response => {
        const detalle = response?.error?.detail;
        this.error.set(detalle || (response?.status === 403
          ? 'La verificación CSRF falló. Reinicia ambos servidores y recarga la página.'
          : 'No fue posible iniciar sesión. Revisa el usuario y la contraseña.'));
        this.enviando.set(false);
      }
    });
  }
}
