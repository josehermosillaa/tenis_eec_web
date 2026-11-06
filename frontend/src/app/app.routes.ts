import { Routes } from '@angular/router';
import { HomeComponent } from './features/home/home.component';
import { LoginComponent } from './features/login/login.component';
import { AdminComponent } from './features/admin/admin.component';
import { adminGuard } from './core/admin.guard';
import { PlayerProfileComponent } from './features/player-profile/player-profile.component';

export const routes: Routes = [
  {path: '', component: HomeComponent, title: 'Ranking · Tenis EEC'},
  {path: 'ranking', redirectTo: '', pathMatch: 'full'},
  {path: 'jugadores/:id', component: PlayerProfileComponent, title: 'Perfil de jugador · Tenis EEC'},
  {path: 'login', component: LoginComponent, title: 'Administración · Tenis EEC'},
  {path: 'admin', component: AdminComponent, canActivate: [adminGuard], title: 'Panel administrativo · Tenis EEC'},
  {path: '**', redirectTo: ''}
];
