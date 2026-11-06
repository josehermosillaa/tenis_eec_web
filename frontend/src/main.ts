import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient, withXsrfConfiguration } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { registerLocaleData } from '@angular/common';
import localeEsCl from '@angular/common/locales/es-CL';
import { AppComponent } from './app/app.component';
import { routes } from './app/app.routes';

registerLocaleData(localeEsCl);

bootstrapApplication(AppComponent, {providers: [
  provideRouter(routes),
  provideHttpClient(withXsrfConfiguration({cookieName: 'csrftoken', headerName: 'X-CSRFToken'}))
]}).catch(console.error);
