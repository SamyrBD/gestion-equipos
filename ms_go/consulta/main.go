// Microservicio de CONSULTA (respaldo) - Go
// Hace lo mismo que el servicio principal (Django Ninja): leer mantenimientos de un equipo.
// Operación: GET /mantenimientos/{equipoID}
package main

import (
	"log"
	"net/http"

	"ms-mantenimientos-go/comun"
)

func main() {
	db := comun.Conectar()
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", comun.Health(db, "consulta-go"))

	mux.HandleFunc("GET /mantenimientos/{equipoID}", func(w http.ResponseWriter, r *http.Request) {
		equipoID, ok := comun.LeerID(r.PathValue("equipoID"))
		if !ok {
			comun.ErrorJSON(w, http.StatusBadRequest, "equipo_id debe ser un número entero positivo")
			return
		}

		// fecha::text evita que el driver convierta la fecha a "2026-09-18T00:00:00Z"
		filas, err := db.QueryContext(r.Context(),
			`SELECT id::int, equipo_id, fecha::text, descripcion, tecnico
			   FROM public.mantenimientos_mantenimiento
			  WHERE equipo_id = $1
			  ORDER BY fecha DESC, id DESC`, equipoID)
		if err != nil {
			log.Println("consulta falló:", err)
			comun.ErrorJSON(w, http.StatusInternalServerError, "No se pudo consultar la base de datos")
			return
		}
		defer filas.Close()

		lista := []comun.Mantenimiento{} // vacía (no nil): el JSON sale [] y no null
		for filas.Next() {
			var m comun.Mantenimiento
			if err := filas.Scan(&m.ID, &m.EquipoID, &m.Fecha, &m.Descripcion, &m.Tecnico); err != nil {
				log.Println("lectura de fila falló:", err)
				comun.ErrorJSON(w, http.StatusInternalServerError, "No se pudo leer el resultado")
				return
			}
			lista = append(lista, m)
		}
		if err := filas.Err(); err != nil {
			log.Println("consulta falló:", err)
			comun.ErrorJSON(w, http.StatusInternalServerError, "No se pudo consultar la base de datos")
			return
		}
		comun.Responder(w, http.StatusOK, lista)
	})

	comun.Iniciar(mux, "consulta-go", "8002")
}