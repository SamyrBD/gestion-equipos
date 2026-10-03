// Microservicio de INSERCIÓN (respaldo) - Go
// Operación: POST /mantenimientos
package main

import (
	"log"
	"net/http"

	"ms-mantenimientos-go/comun"
)

func main() {
	db := comun.Conectar()
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", comun.Health(db, "insertar-go"))

	mux.HandleFunc("POST /mantenimientos", func(w http.ResponseWriter, r *http.Request) {
		var m comun.Mantenimiento
		if !comun.LeerJSON(w, r, &m) {
			return
		}
		m.Limpiar()

		// 1) Validar ANTES de tocar la base de datos
		if m.EquipoID <= 0 {
			comun.ErrorJSON(w, http.StatusBadRequest, "equipo_id debe ser un número entero positivo")
			return
		}
		if problema := m.Validar(); problema != "" {
			comun.ErrorJSON(w, http.StatusBadRequest, problema)
			return
		}

		// 2) Insertar y devolver la fila creada (con su id)
		err := db.QueryRowContext(r.Context(),
			`INSERT INTO public.mantenimientos_mantenimiento (equipo_id, fecha, descripcion, tecnico)
			 VALUES ($1, $2, $3, $4)
			 RETURNING id::int, equipo_id, fecha::text, descripcion, tecnico`,
			m.EquipoID, m.Fecha, m.Descripcion, m.Tecnico,
		).Scan(&m.ID, &m.EquipoID, &m.Fecha, &m.Descripcion, &m.Tecnico)
		if err != nil {
			log.Println("insertar falló:", err)
			if comun.EsErrorDeDatos(err) {
				comun.ErrorJSON(w, http.StatusBadRequest, "Alguno de los datos no es válido")
				return
			}
			comun.ErrorJSON(w, http.StatusInternalServerError, "No se pudo guardar el mantenimiento")
			return
		}
		comun.Responder(w, http.StatusCreated, m)
	})

	comun.Iniciar(mux, "insertar-go", "8006")
}