export interface Liga {id: number; nombre: string; fecha_inicio: string; fecha_fin: string | null; estado: string; es_principal: boolean; descripcion: string;}
export interface Categoria {id: number; nombre: string;}
export interface Division {id: number; liga: number; nombre: string; orden: number; estado: string; categorias: Categoria[]; cantidad_inscripciones: number; cantidad_inscripciones_activas: number; puede_eliminar: boolean;}
export interface Ranking {posicion: number; inscripcion_id: number; jugador_id: number; jugador: string; categoria: string; puntos_partidos: number; puntos_torneos: number; puntos_totales: number; partidos: number; ganados: number; perdidos: number; diferencia_sets: number; diferencia_juegos: number;}
export interface Partido {id: number; division: number; fecha: string; jugador_a: number; jugador_a_nombre: string; jugador_b: number; jugador_b_nombre: string; ganador_nombre: string; set_1: string; set_2: string; super_tiebreak: string; estado: string;}
export interface Inscripcion {id: number; categoria_historica: string; activa: boolean; jugador_detalle: {id: number; nombre: string; estado: string;};}
export interface Usuario {id: number; username: string;}
export interface InscripcionActiva {id: number; division: number; division_nombre: string; liga_nombre: string; categoria_historica: string;}
export interface Jugador {id: number; nombre: string; categoria: number; categoria_nombre: string; estado: string; inscripciones_activas: InscripcionActiva[];}
export interface Torneo {id: number; liga: number; nombre: string; fecha: string; descripcion: string; anulado: boolean;}
export interface PerfilPartido {id: number; fecha: string; rival: string; ganado: boolean; set_1: string; set_2: string; super_tiebreak: string;}
export interface PerfilEstadisticas {posicion: number; puntos_partidos: number; puntos_torneos: number; puntos_totales: number; partidos: number; ganados: number; perdidos: number; diferencia_sets: number; diferencia_juegos: number;}
export interface PerfilRanking {posicion: number; jugador_id: number; jugador: string; categoria: string; partidos: number; ganados: number; perdidos: number; diferencia_sets: number; puntos_totales: number;}
export interface PerfilJugador {jugador: Jugador; liga: Liga|null; division: Division|null; estadisticas: PerfilEstadisticas; partidos: PerfilPartido[]; ranking: PerfilRanking[];}
