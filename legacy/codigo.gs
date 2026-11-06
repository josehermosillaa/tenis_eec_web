// =======================================================
// CONFIGURACIÓN DE CATEGORÍAS
// =======================================================

const CATEGORIAS = {

  "3ra": {
    jugadores: "Lista Jugadores 3ra",
    resultados: "RESULTADOS 3ra",
    ranking: "RANKING 3ra"
  },

  "4ta": {
    jugadores: "Lista Jugadores 4Ta",
    resultados: "RESULTADOS 4ta",
    ranking: "RANKING 4ta"
  }

};


const FILA_CABECERA = 4;
const FILA_INICIO = 5;


// =======================================================
// ON EDIT
// =======================================================

function onEdit(e) {

  if (!e || !e.range) return;

  const hoja = e.range.getSheet();
  const nombreHoja = hoja.getName();


  // =====================================================
  // BUSCAR CATEGORÍA
  // =====================================================

  for (const categoria in CATEGORIAS) {

    const config = CATEGORIAS[categoria];


    // ===================================================
    // RESULTADOS
    // ===================================================

    if (nombreHoja === config.resultados) {

      procesarResultado(e, categoria);

      return;
    }


    // ===================================================
    // LISTA DE JUGADORES
    // ===================================================

    if (nombreHoja === config.jugadores) {

      if (
        e.range.getColumn() >= 1 &&
        e.range.getColumn() <= 7
      ) {

        actualizarDropdownsCategoria(categoria);

        actualizarRankingCategoria(categoria);

      }

      return;
    }

  }

}


// =======================================================
// PROCESAR EDICIÓN DE RESULTADOS
// =======================================================

function procesarResultado(e, categoria) {

  const hoja = e.range.getSheet();

  const fila = e.range.getRow();
  const columna = e.range.getColumn();


  if (fila < 2) return;


  // A = Fecha
  // B = Jugador A
  // C = SET 1
  // D = SET 2
  // E = SUPER TIEBREAK
  // F = Jugador B
  // G = Estado
  // H = Ganador


  if (
    columna < 2 ||
    columna > 8
  ) {

    return;

  }


  // =====================================================
  // SETS Y SUPER TIEBREAK COMO TEXTO
  // =====================================================

  hoja
    .getRange("C:E")
    .setNumberFormat("@");


  // =====================================================
  // FECHA AUTOMÁTICA
  // =====================================================

  const datos =
    hoja
      .getRange(
        fila,
        2,
        1,
        5
      )
      .getValues()[0];


  const hayDatos =
    datos.some(
      valor => valor !== ""
    );


  const fecha =
    hoja.getRange(
      fila,
      1
    );


  if (
    hayDatos &&
    fecha.getValue() === ""
  ) {

    fecha.setValue(
      new Date()
    );

    fecha.setNumberFormat(
      "d/m/yyyy"
    );

  }


  // =====================================================
  // JUGADORES
  // =====================================================

  const jugadorA =
    hoja
      .getRange(fila, 2)
      .getDisplayValue()
      .trim();


  const jugadorB =
    hoja
      .getRange(fila, 6)
      .getDisplayValue()
      .trim();


  // =====================================================
  // NO PERMITIR JUGADOR RETIRADO EN PARTIDOS NUEVOS
  // =====================================================

  if (
    columna === 2 ||
    columna === 6
  ) {

    const jugadorEditado =
      columna === 2
        ? jugadorA
        : jugadorB;

    if (
      jugadorEditado !== "" &&
      !jugadorEstaActivo(
        categoria,
        jugadorEditado
      )
    ) {

      hoja
        .getRange(fila, columna)
        .clearContent();

      SpreadsheetApp
        .getActiveSpreadsheet()
        .toast(
          "El jugador está RETIRADO y no puede ser seleccionado para un partido nuevo.",
          "Jugador retirado",
          5
        );

      actualizarEstado(
        hoja,
        fila
      );

      actualizarRankingCategoria(
        categoria
      );

      return;
    }
  }


  // =====================================================
  // NO PERMITIR MISMO JUGADOR
  // =====================================================

  if (
    jugadorA !== "" &&
    jugadorB !== "" &&
    jugadorA === jugadorB
  ) {

    if (columna === 6) {

      hoja
        .getRange(fila, 6)
        .clearContent();

    }

    else if (columna === 2) {

      hoja
        .getRange(fila, 2)
        .clearContent();

    }


    SpreadsheetApp
      .getActiveSpreadsheet()
      .toast(
        "Jugador A y Jugador B no pueden ser iguales.",
        "Partido inválido",
        4
      );


    actualizarEstado(
      hoja,
      fila
    );


    actualizarRankingCategoria(
      categoria
    );


    return;
  }


  // =====================================================
  // SET 1 / SET 2
  // =====================================================

  if (
    columna === 3 ||
    columna === 4
  ) {

    validarSet(
      hoja,
      fila,
      columna
    );


    actualizarEstado(
      hoja,
      fila
    );


    actualizarRankingCategoria(
      categoria
    );


    return;
  }


  // =====================================================
  // SUPER TIEBREAK
  // =====================================================

  if (columna === 5) {

    validarSuperTiebreak(
      hoja,
      fila
    );


    actualizarEstado(
      hoja,
      fila
    );


    actualizarRankingCategoria(
      categoria
    );


    return;
  }


  // =====================================================
  // JUGADORES
  // =====================================================

  if (
    columna === 2 ||
    columna === 6
  ) {

    actualizarEstado(
      hoja,
      fila
    );


    actualizarRankingCategoria(
      categoria
    );


    return;
  }

}


// =======================================================
// VALIDAR SET
// =======================================================

function validarSet(
  hoja,
  fila,
  columna
) {

  const celda =
    hoja.getRange(
      fila,
      columna
    );


  const valor =
    celda
      .getDisplayValue()
      .trim();


  // Permitir borrar
  if (valor === "") {

    actualizarSuperTiebreakVisual(
      hoja,
      fila
    );

    return;
  }


  // =====================================================
  // FORMATO
  // =====================================================

  const match =
    valor.match(
      /^(\d+)\s*[\/-]\s*(\d+)$/
    );


  if (!match) {

    celda.clearContent();


    SpreadsheetApp
      .getActiveSpreadsheet()
      .toast(
        "Formato inválido. Usa 6/4, 7/5 o 7-6.",
        "SET inválido",
        4
      );


    return;
  }


  const n1 =
    Number(match[1]);


  const n2 =
    Number(match[2]);


  // =====================================================
  // RESULTADOS VÁLIDOS
  // =====================================================

  const validos = [

    [6, 0],
    [6, 1],
    [6, 2],
    [6, 3],
    [6, 4],
    [7, 5],
    [7, 6]

  ];


  const valido =
    validos.some(
      resultado => {

        return (

          (
            n1 === resultado[0] &&
            n2 === resultado[1]
          )

          ||

          (
            n1 === resultado[1] &&
            n2 === resultado[0]
          )

        );

      }
    );


  if (!valido) {

    celda.clearContent();


    SpreadsheetApp
      .getActiveSpreadsheet()
      .toast(
        "Resultado inválido. Usa 6/0, 6/1, 6/2, 6/3, 6/4, 7/5 o 7/6.",
        "SET inválido",
        5
      );


    return;
  }


  actualizarSuperTiebreakVisual(
    hoja,
    fila
  );

}


// =======================================================
// VALIDAR SUPER TIEBREAK
// =======================================================

function validarSuperTiebreak(
  hoja,
  fila
) {

  const celda =
    hoja.getRange(
      fila,
      5
    );


  const valor =
    celda
      .getDisplayValue()
      .trim();


  // Permitir vacío
  if (valor === "") {

    return;
  }


  // =====================================================
  // DEBE EXISTIR 1 SET A 1 SET
  // =====================================================

  if (
    !superTiebreakPermitido(
      hoja,
      fila
    )
  ) {

    celda.clearContent();


    bloquearSuperTiebreak(
      celda
    );


    SpreadsheetApp
      .getActiveSpreadsheet()
      .toast(
        "No corresponde Super Tiebreak. Un jugador ya ganó los dos sets.",
        "Super Tiebreak",
        5
      );


    return;
  }


  // =====================================================
  // FORMATO
  // =====================================================

  const match =
    valor.match(
      /^(\d+)\s*[\/-]\s*(\d+)$/
    );


  if (!match) {

    celda.clearContent();


    SpreadsheetApp
      .getActiveSpreadsheet()
      .toast(
        "Formato inválido. Ejemplo: 10/8, 10/0, 11/9, 12/10.",
        "Super Tiebreak",
        5
      );


    return;
  }


  const n1 =
    Number(match[1]);


  const n2 =
    Number(match[2]);


  const mayor =
    Math.max(
      n1,
      n2
    );


  const diferencia =
    Math.abs(
      n1 - n2
    );


  let valido = false;


  // =====================================================
  // HASTA 10
  // =====================================================

  if (
    mayor === 10 &&
    diferencia >= 2
  ) {

    valido = true;

  }


  // =====================================================
  // DESPUÉS DE 9-9
  // =====================================================

  else if (
    mayor > 10 &&
    diferencia === 2
  ) {

    valido = true;

  }


  // =====================================================
  // INVALIDO
  // =====================================================

  if (!valido) {

    celda.clearContent();


    SpreadsheetApp
      .getActiveSpreadsheet()
      .toast(
        "Super Tiebreak inválido. A 10 se gana por 2. Después de 9-9 debe continuar hasta conseguir exactamente 2 de diferencia.",
        "Super Tiebreak",
        7
      );


    return;
  }

}


// =======================================================
// COMPROBAR SI SUPER TIEBREAK ESTÁ PERMITIDO
// =======================================================

function superTiebreakPermitido(
  hoja,
  fila
) {

  const set1 =
    hoja
      .getRange(fila, 3)
      .getDisplayValue()
      .trim();


  const set2 =
    hoja
      .getRange(fila, 4)
      .getDisplayValue()
      .trim();


  if (
    set1 === "" ||
    set2 === ""
  ) {

    return false;

  }


  const ganador1 =
    obtenerGanadorSet(
      set1
    );


  const ganador2 =
    obtenerGanadorSet(
      set2
    );


  if (
    ganador1 === null ||
    ganador2 === null
  ) {

    return false;

  }


  // Un jugador ganó ambos sets
  if (
    ganador1 === ganador2
  ) {

    return false;

  }


  // 1 set para cada jugador
  return true;

}


// =======================================================
// OBTENER GANADOR DE SET
// =======================================================

function obtenerGanadorSet(
  valor
) {

  const match =
    valor.match(
      /^(\d+)\s*[\/-]\s*(\d+)$/
    );


  if (!match) {

    return null;

  }


  const n1 =
    Number(match[1]);


  const n2 =
    Number(match[2]);


  if (n1 > n2) {

    return 1;

  }


  if (n2 > n1) {

    return 2;

  }


  return null;

}


// =======================================================
// OBTENER GANADOR SUPER TIEBREAK
// =======================================================

function obtenerGanadorSuper(
  valor
) {

  const match =
    valor.match(
      /^(\d+)\s*[\/-]\s*(\d+)$/
    );


  if (!match) {

    return null;

  }


  const n1 =
    Number(match[1]);


  const n2 =
    Number(match[2]);


  const mayor =
    Math.max(
      n1,
      n2
    );


  const diferencia =
    Math.abs(
      n1 - n2
    );


  // =====================================================
  // 10-x
  // =====================================================

  if (
    mayor === 10 &&
    diferencia >= 2
  ) {

    return n1 > n2
      ? 1
      : 2;

  }


  // =====================================================
  // DESPUÉS DE 9-9
  // =====================================================

  if (
    mayor > 10 &&
    diferencia === 2
  ) {

    return n1 > n2
      ? 1
      : 2;

  }


  return null;

}


// =======================================================
// ACTUALIZAR ESTADO DEL PARTIDO
// =======================================================

function actualizarEstado(
  hoja,
  fila
) {

  const jugadorA =
    hoja
      .getRange(fila, 2)
      .getDisplayValue()
      .trim();


  const set1 =
    hoja
      .getRange(fila, 3)
      .getDisplayValue()
      .trim();


  const set2 =
    hoja
      .getRange(fila, 4)
      .getDisplayValue()
      .trim();


  const superTiebreak =
    hoja
      .getRange(fila, 5)
      .getDisplayValue()
      .trim();


  const jugadorB =
    hoja
      .getRange(fila, 6)
      .getDisplayValue()
      .trim();


  const estado =
    hoja.getRange(
      fila,
      7
    );


  const ganador =
    hoja.getRange(
      fila,
      8
    );


  // =====================================================
  // FALTAN JUGADORES
  // =====================================================

  if (
    jugadorA === "" ||
    jugadorB === ""
  ) {

    estado.clearContent();

    ganador.clearContent();


    desbloquearSuperTiebreak(
      hoja.getRange(fila, 5)
    );


    return;
  }


  // =====================================================
  // FALTAN SETS
  // =====================================================

  if (
    set1 === "" ||
    set2 === ""
  ) {

    estado.setValue(
      "PENDIENTE"
    );


    ganador.clearContent();


    desbloquearSuperTiebreak(
      hoja.getRange(fila, 5)
    );


    return;
  }


  const ganador1 =
    obtenerGanadorSet(
      set1
    );


  const ganador2 =
    obtenerGanadorSet(
      set2
    );


  if (
    ganador1 === null ||
    ganador2 === null
  ) {

    estado.setValue(
      "PENDIENTE"
    );


    ganador.clearContent();


    return;
  }


  // =====================================================
  // GANÓ LOS DOS SETS
  // =====================================================

  if (
    ganador1 === ganador2
  ) {

    const nombreGanador =
      ganador1 === 1
        ? jugadorA
        : jugadorB;


    if (
      superTiebreak !== ""
    ) {

      hoja
        .getRange(fila, 5)
        .clearContent();

    }


    bloquearSuperTiebreak(
      hoja.getRange(fila, 5)
    );


    estado.setValue(
      "TERMINADO"
    );


    ganador.setValue(
      nombreGanador
    );


    return;
  }


  // =====================================================
  // 1 SET CADA UNO
  // =====================================================

  if (
    superTiebreak === ""
  ) {

    estado.setValue(
      "PENDIENTE"
    );


    ganador.clearContent();


    desbloquearSuperTiebreak(
      hoja.getRange(fila, 5)
    );


    return;
  }


  const ganadorST =
    obtenerGanadorSuper(
      superTiebreak
    );


  if (
    ganadorST === null
  ) {

    estado.setValue(
      "PENDIENTE"
    );


    ganador.clearContent();


    return;
  }


  const nombreGanador =
    ganadorST === 1
      ? jugadorA
      : jugadorB;


  estado.setValue(
    "TERMINADO"
  );


  ganador.setValue(
    nombreGanador
  );

}


// =======================================================
// ACTUALIZAR ESTADO VISUAL SUPER TIEBREAK
// =======================================================

function actualizarSuperTiebreakVisual(
  hoja,
  fila
) {

  const celda =
    hoja.getRange(
      fila,
      5
    );


  const set1 =
    hoja
      .getRange(fila, 3)
      .getDisplayValue()
      .trim();


  const set2 =
    hoja
      .getRange(fila, 4)
      .getDisplayValue()
      .trim();


  if (
    set1 === "" ||
    set2 === ""
  ) {

    desbloquearSuperTiebreak(
      celda
    );


    return;
  }


  const ganador1 =
    obtenerGanadorSet(
      set1
    );


  const ganador2 =
    obtenerGanadorSet(
      set2
    );


  // =====================================================
  // MISMO GANADOR EN LOS DOS SETS
  // =====================================================

  if (
    ganador1 !== null &&
    ganador2 !== null &&
    ganador1 === ganador2
  ) {

    celda.clearContent();


    bloquearSuperTiebreak(
      celda
    );


    return;
  }


  desbloquearSuperTiebreak(
    celda
  );

}


// =======================================================
// BLOQUEAR SUPER TIEBREAK
// =======================================================

function bloquearSuperTiebreak(
  celda
) {

  celda.setBackground(
    "#d9d9d9"
  );


  celda.setFontColor(
    "#808080"
  );

}


// =======================================================
// DESBLOQUEAR SUPER TIEBREAK
// =======================================================

function desbloquearSuperTiebreak(
  celda
) {

  celda.setBackground(null);

  celda.setFontColor(null);

}


// =======================================================
// COMPROBAR SI UN JUGADOR ESTÁ ACTIVO
// =======================================================

function jugadorEstaActivo(
  categoria,
  jugador
) {

  const config =
    CATEGORIAS[categoria];

  if (!config) return false;


  const ss =
    SpreadsheetApp
      .getActiveSpreadsheet();


  const lista =
    ss.getSheetByName(
      config.jugadores
    );


  if (!lista) return false;


  const ultimaFila =
    lista.getLastRow();


  if (ultimaFila < 2) {
    return false;
  }


  const datos =
    lista
      .getRange(
        2,
        1,
        ultimaFila - 1,
        3
      )
      .getValues();


  for (
    let i = 0;
    i < datos.length;
    i++
  ) {

    const nombre =
      String(
        datos[i][0] || ""
      ).trim();


    if (nombre !== jugador) {
      continue;
    }


    const estado =
      String(
        datos[i][2] || "ACTIVO"
      )
        .trim()
        .toUpperCase();


    return estado !== "RETIRADO";
  }


  return false;
}


// =======================================================
// ACTUALIZAR DROPDOWNS DE JUGADORES ACTIVOS
// =======================================================

function actualizarDropdownsCategoria(
  categoria
) {

  const config =
    CATEGORIAS[categoria];

  if (!config) return;


  const ss =
    SpreadsheetApp
      .getActiveSpreadsheet();


  const lista =
    ss.getSheetByName(
      config.jugadores
    );


  const resultados =
    ss.getSheetByName(
      config.resultados
    );


  if (
    !lista ||
    !resultados
  ) {
    return;
  }


  const ultimaFila =
    lista.getLastRow();


  const jugadoresActivos = [];


  if (ultimaFila >= 2) {

    const datos =
      lista
        .getRange(
          2,
          1,
          ultimaFila - 1,
          3
        )
        .getValues();


    datos.forEach(
      fila => {

        const jugador =
          String(
            fila[0] || ""
          ).trim();


        const estado =
          String(
            fila[2] || "ACTIVO"
          )
            .trim()
            .toUpperCase();


        if (
          jugador !== "" &&
          estado !== "RETIRADO"
        ) {

          jugadoresActivos.push(
            jugador
          );

        }

      }
    );

  }


  const cantidadFilas =
    Math.max(
      resultados.getMaxRows() - 1,
      1
    );


  const rangoJugadorA =
    resultados.getRange(
      2,
      2,
      cantidadFilas,
      1
    );


  const rangoJugadorB =
    resultados.getRange(
      2,
      6,
      cantidadFilas,
      1
    );


  if (jugadoresActivos.length === 0) {

    rangoJugadorA
      .clearDataValidations();

    rangoJugadorB
      .clearDataValidations();

    return;
  }


  const regla =
    SpreadsheetApp
      .newDataValidation()
      .requireValueInList(
        jugadoresActivos,
        true
      )
      // Permitimos valores históricos ya escritos.
      // Si alguien intenta seleccionar/escribir un retirado
      // en una edición nueva, onEdit lo rechaza.
      .setAllowInvalid(true)
      .build();


  rangoJugadorA
    .setDataValidation(
      regla
    );


  rangoJugadorB
    .setDataValidation(
      regla
    );
}


// =======================================================
// ACTUALIZAR TODOS LOS RANKINGS
// =======================================================

function actualizarTodosLosRankings() {

  for (
    const categoria in CATEGORIAS
  ) {

    actualizarDropdownsCategoria(
      categoria
    );


    actualizarRankingCategoria(
      categoria
    );

  }

}


// =======================================================
// ACTUALIZAR RANKING DE UNA CATEGORÍA
// =======================================================

function actualizarRankingCategoria(
  categoria
) {

  const config =
    CATEGORIAS[categoria];


  if (!config) return;


  const ss =
    SpreadsheetApp
      .getActiveSpreadsheet();


  const resultados =
    ss.getSheetByName(
      config.resultados
    );


  const ranking =
    ss.getSheetByName(
      config.ranking
    );


  const lista =
    ss.getSheetByName(
      config.jugadores
    );


  if (
    !resultados ||
    !ranking ||
    !lista
  ) {

    return;

  }


  // =====================================================
  // OBTENER JUGADORES
  // =====================================================

  const ultimaFila =
    lista.getLastRow();


  if (
    ultimaFila < 2
  ) {

    return;

  }


  const datosJugadores =
    lista
      .getRange(
        2,
        1,
        ultimaFila - 1,
        7
      )
      .getValues();


  const jugadores = [];

  const estadosJugadores = {};

  const torneos = {};


  datosJugadores.forEach(
    fila => {

      const jugador =
        String(
          fila[0] || ""
        ).trim();


      if (
        jugador === ""
      ) {

        return;

      }


      jugadores.push(
        jugador
      );


      // C = Estado
      // Si está vacío se considera ACTIVO para mantener
      // compatibilidad con jugadores antiguos.
      const estadoJugador =
        String(
          fila[2] || "ACTIVO"
        )
          .trim()
          .toUpperCase();


      estadosJugadores[jugador] =
        estadoJugador;


      // D:G = puntos de torneos
      const IN =
        Number(fila[3]) || 0;


      const AGO =
        Number(fila[4]) || 0;


      const SEP =
        Number(fila[5]) || 0;


      const OCT =
        Number(fila[6]) || 0;


      torneos[jugador] = {

        IN: IN,

        AGO: AGO,

        SEP: SEP,

        OCT: OCT,

        total:
          IN +
          AGO +
          SEP +
          OCT

      };

    }
  );


  // =====================================================
  // ESTADÍSTICAS
  // =====================================================

  const estadisticas = {};


  jugadores.forEach(
    jugador => {

      estadisticas[jugador] = {

        puntosPartidos: 0,

        puntosTorneos:
          torneos[jugador].total,

        puntosTotales: 0,

        partidos: 0,

        ganados: 0,

        perdidos: 0,

        setsGanados: 0,

        setsPerdidos: 0,

        juegosGanados: 0,

        juegosPerdidos: 0

      };

    }
  );


  // =====================================================
  // LEER RESULTADOS
  // =====================================================

  const ultimaFilaResultados =
    resultados.getLastRow();


  if (
    ultimaFilaResultados >= 2
  ) {

    const datos =
      resultados
        .getRange(
          2,
          1,
          ultimaFilaResultados - 1,
          8
        )
        .getValues();


    datos.forEach(
      fila => {

        const jugadorA =
          String(
            fila[1] || ""
          ).trim();


        const set1 =
          String(
            fila[2] || ""
          ).trim();


        const set2 =
          String(
            fila[3] || ""
          ).trim();


        const superTiebreak =
          String(
            fila[4] || ""
          ).trim();


        const jugadorB =
          String(
            fila[5] || ""
          ).trim();


        const estado =
          String(
            fila[6] || ""
          ).trim();


        const ganador =
          String(
            fila[7] || ""
          ).trim();


        // =================================================
        // SOLO PARTIDOS TERMINADOS
        // =================================================

        if (
          estado !== "TERMINADO"
        ) {

          return;

        }


        if (
          jugadorA === "" ||
          jugadorB === "" ||
          set1 === "" ||
          set2 === "" ||
          ganador === ""
        ) {

          return;

        }


        if (
          !estadisticas[jugadorA] ||
          !estadisticas[jugadorB]
        ) {

          return;

        }


        const A =
          estadisticas[jugadorA];


        const B =
          estadisticas[jugadorB];


        // =================================================
        // PARTIDOS
        // =================================================

        A.partidos++;
        B.partidos++;


        // =================================================
        // GANADOR / PERDEDOR
        // =================================================

        if (
          ganador === jugadorA
        ) {

          A.ganados++;
          B.perdidos++;

        }

        else if (
          ganador === jugadorB
        ) {

          B.ganados++;
          A.perdidos++;

        }

        else {

          return;

        }


        // =================================================
        // PUNTOS DE PARTIDOS
        // =================================================

        if (
          superTiebreak !== ""
        ) {

          // Victoria Super Tiebreak = 3
          // Derrota Super Tiebreak = 2

          if (
            ganador === jugadorA
          ) {

            A.puntosPartidos += 3;
            B.puntosPartidos += 2;

          }

          else {

            B.puntosPartidos += 3;
            A.puntosPartidos += 2;

          }

        }

        else {

          // Victoria normal = 3
          // Derrota normal = 1

          if (
            ganador === jugadorA
          ) {

            A.puntosPartidos += 3;
            B.puntosPartidos += 1;

          }

          else {

            B.puntosPartidos += 3;
            A.puntosPartidos += 1;

          }

        }


        // =================================================
        // SETS NORMALES Y JUEGOS
        // =================================================

        procesarSetRanking(
          set1,
          A,
          B
        );


        procesarSetRanking(
          set2,
          A,
          B
        );


        // =================================================
        // SUPER TIEBREAK COMO SET
        //
        // IMPORTANTE:
        //
        // SÍ suma como SET ganado/perdido.
        //
        // NO suma como JUEGOS.
        //
        // =================================================

        if (
          superTiebreak !== ""
        ) {

          const ganadorST =
            obtenerGanadorSuper(
              superTiebreak
            );


          if (
            ganadorST === 1
          ) {

            // Jugador A ganó el
            // Super Tiebreak

            A.setsGanados++;

            B.setsPerdidos++;

          }

          else if (
            ganadorST === 2
          ) {

            // Jugador B ganó el
            // Super Tiebreak

            B.setsGanados++;

            A.setsPerdidos++;

          }

        }

      }
    );

  }


  // =====================================================
  // PUNTOS TOTALES
  // =====================================================

  jugadores.forEach(
    jugador => {

      const s =
        estadisticas[jugador];


      s.puntosTotales =
        s.puntosPartidos +
        s.puntosTorneos;

    }
  );


  // =====================================================
  // CREAR DATOS DEL RANKING
  // =====================================================

  const datosRanking =
    jugadores
      .filter(
        jugador =>
          estadosJugadores[jugador] !==
          "RETIRADO"
      )
      .map(
      jugador => {

        const s =
          estadisticas[jugador];


        return {

          jugador:
            jugador,

          puntosPartidos:
            s.puntosPartidos,

          puntosTorneos:
            s.puntosTorneos,

          puntosTotales:
            s.puntosTotales,

          partidos:
            s.partidos,

          ganados:
            s.ganados,

          perdidos:
            s.perdidos,

          setsGanados:
            s.setsGanados,

          setsPerdidos:
            s.setsPerdidos,

          diferenciaSets:
            s.setsGanados -
            s.setsPerdidos,

          juegosGanados:
            s.juegosGanados,

          juegosPerdidos:
            s.juegosPerdidos,

          diferenciaJuegos:
            s.juegosGanados -
            s.juegosPerdidos

        };

      }
    );


  // =====================================================
  // ORDEN DEL RANKING
  // =====================================================

  datosRanking.sort(
    (a, b) => {

      // 1. PUNTOS TOTALES

      if (
        b.puntosTotales !==
        a.puntosTotales
      ) {

        return (
          b.puntosTotales -
          a.puntosTotales
        );

      }


      // 2. DIFERENCIA DE SETS

      if (
        b.diferenciaSets !==
        a.diferenciaSets
      ) {

        return (
          b.diferenciaSets -
          a.diferenciaSets
        );

      }


      // 3. DIFERENCIA DE JUEGOS

      if (
        b.diferenciaJuegos !==
        a.diferenciaJuegos
      ) {

        return (
          b.diferenciaJuegos -
          a.diferenciaJuegos
        );

      }


      // 4. JUEGOS GANADOS

      if (
        b.juegosGanados !==
        a.juegosGanados
      ) {

        return (
          b.juegosGanados -
          a.juegosGanados
        );

      }


      // 5. ALFABÉTICO

      return a.jugador.localeCompare(
        b.jugador
      );

    }
  );


  // =====================================================
  // LIMPIAR RANKING
  // =====================================================

  const filas =
    ranking.getMaxRows() -
    FILA_INICIO +
    1;


  if (
    filas > 0
  ) {

    // Tabla principal A:M

    ranking
      .getRange(
        FILA_INICIO,
        1,
        filas,
        13
      )
      .clearContent();


    // Tabla torneos N:T

    ranking
      .getRange(
        FILA_INICIO,
        14,
        filas,
        7
      )
      .clearContent();

  }


  // =====================================================
  // CABECERA PRINCIPAL
  // =====================================================

  ranking
    .getRange(
      FILA_CABECERA,
      1,
      1,
      13
    )
    .setValues([

      [
        "#",
        "Jugadores",
        "Puntos Partidos",
        "Puntos Totales",
        "Partidos",
        "Partidos ganados",
        "Partidos perdidos",
        "Sets ganados",
        "Sets perdidos",
        "Difer sets",
        "Juegos Ganados",
        "Juegos Perdidos",
        "Dif Juegos"
      ]

    ]);


  // =====================================================
  // CABECERA TORNEOS
  // =====================================================

  ranking
    .getRange(
      FILA_CABECERA,
      14,
      1,
      7
    )
    .setValues([

      [
        "#",
        "Jugador",
        "Torneo IN",
        "Torneo AGO",
        "Torneo SEP",
        "Torneo OCT",
        "Total Torneos"
      ]

    ]);


  // =====================================================
  // SALIDA RANKING
  // =====================================================

  const salida = [];


  datosRanking.forEach(
    (s, index) => {

      salida.push([

        // A
        index + 1,

        // B
        s.jugador,

        // C
        s.puntosPartidos,

        // D
        s.puntosTotales,

        // E
        s.partidos,

        // F
        s.ganados,

        // G
        s.perdidos,

        // H
        s.setsGanados,

        // I
        s.setsPerdidos,

        // J
        s.diferenciaSets,

        // K
        s.juegosGanados,

        // L
        s.juegosPerdidos,

        // M
        s.diferenciaJuegos

      ]);

    }
  );


  if (
    salida.length > 0
  ) {

    ranking
      .getRange(
        FILA_INICIO,
        1,
        salida.length,
        13
      )
      .setValues(
        salida
      );

  }


  // =====================================================
  // TABLA DE TORNEOS
  // =====================================================

  const salidaTorneos = [];


  datosRanking.forEach(
    (s, index) => {

      const torneo =
        torneos[s.jugador];


      salidaTorneos.push([

        index + 1,

        s.jugador,

        torneo.IN,

        torneo.AGO,

        torneo.SEP,

        torneo.OCT,

        torneo.total

      ]);

    }
  );


  if (
    salidaTorneos.length > 0
  ) {

    ranking
      .getRange(
        FILA_INICIO,
        14,
        salidaTorneos.length,
        7
      )
      .setValues(
        salidaTorneos
      );

  }


  // =====================================================
  // FORMATO
  // =====================================================

  ranking
    .getRange(
      FILA_CABECERA,
      1,
      1,
      13
    )
    .setFontWeight(
      "bold"
    );


  ranking
    .getRange(
      FILA_CABECERA,
      14,
      1,
      7
    )
    .setFontWeight(
      "bold"
    );


  ranking
    .getRange(
      FILA_CABECERA,
      1,
      1,
      20
    )
    .setHorizontalAlignment(
      "center"
    );


  // =====================================================
  // PROTEGER
  // =====================================================

  protegerRanking(
    ranking,
    categoria
  );

}


// =======================================================
// PROCESAR SET NORMAL
//
// SUMA:
// - Sets
// - Juegos
// =======================================================

function procesarSetRanking(
  resultado,
  jugadorA,
  jugadorB
) {

  const match =
    resultado.match(
      /^(\d+)\s*[\/-]\s*(\d+)$/
    );


  if (!match) {

    return;

  }


  const juegosA =
    Number(match[1]);


  const juegosB =
    Number(match[2]);


  // =====================================================
  // JUEGOS
  // =====================================================

  jugadorA.juegosGanados +=
    juegosA;


  jugadorA.juegosPerdidos +=
    juegosB;


  jugadorB.juegosGanados +=
    juegosB;


  jugadorB.juegosPerdidos +=
    juegosA;


  // =====================================================
  // SETS
  // =====================================================

  if (
    juegosA > juegosB
  ) {

    jugadorA.setsGanados++;

    jugadorB.setsPerdidos++;

  }

  else if (
    juegosB > juegosA
  ) {

    jugadorB.setsGanados++;

    jugadorA.setsPerdidos++;

  }

}


// =======================================================
// PROTEGER RANKING
// =======================================================

function protegerRanking(
  hoja,
  categoria
) {

  const descripcion =
    "RANKING_" +
    categoria.toUpperCase() +
    "_PROTEGIDO";


  const protecciones =
    hoja.getProtections(
      SpreadsheetApp
        .ProtectionType
        .SHEET
    );


  let proteccion = null;


  protecciones.forEach(
    p => {

      if (
        p.getDescription() ===
        descripcion
      ) {

        proteccion = p;

      }

    }
  );


  if (!proteccion) {

    proteccion =
      hoja
        .protect()
        .setDescription(
          descripcion
        );

  }


  proteccion.setWarningOnly(
    false
  );


  if (
    proteccion.canDomainEdit()
  ) {

    proteccion.setDomainEdit(
      false
    );

  }

}


// =======================================================
// MENÚ
// =======================================================

function onOpen() {

  SpreadsheetApp
    .getUi()
    .createMenu(
      "🎾 Ranking Tenis"
    )

    .addItem(
      "Actualizar 3ra",
      "actualizar3ra"
    )

    .addItem(
      "Actualizar 4ta",
      "actualizar4ta"
    )

    .addItem(
      "Actualizar todos",
      "actualizarTodosLosRankings"
    )

    .addSeparator()

    .addItem(
      "Proteger rankings",
      "protegerTodosLosRankings"
    )

    .addToUi();

}


// =======================================================
// ATAJO 3RA
// =======================================================

function actualizar3ra() {

  actualizarDropdownsCategoria(
    "3ra"
  );


  actualizarRankingCategoria(
    "3ra"
  );

}


// =======================================================
// ATAJO 4TA
// =======================================================

function actualizar4ta() {

  actualizarDropdownsCategoria(
    "4ta"
  );


  actualizarRankingCategoria(
    "4ta"
  );

}


// =======================================================
// PROTEGER TODOS LOS RANKINGS
// =======================================================

function protegerTodosLosRankings() {

  for (
    const categoria in CATEGORIAS
  ) {

    const config =
      CATEGORIAS[categoria];


    const ss =
      SpreadsheetApp
        .getActiveSpreadsheet();


    const ranking =
      ss.getSheetByName(
        config.ranking
      );


    if (ranking) {

      protegerRanking(
        ranking,
        categoria
      );

    }

  }


  SpreadsheetApp
    .getUi()
    .alert(
      "RANKING 3ra y RANKING 4ta protegidos correctamente."
    );

}