// Microservicio de ACTUALIZACIÓN (respaldo) - Go
// Operación: PUT /mantenimientos/{id}
package main

import (
	"database/sql"
	"errors"
	"log"
	"net/http"

	"ms-mantenimientos-go/comun"
)

func main() {
	db := comun.Conectar()
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", comun.Health(db, "actualizar-go"))

	mux.HandleFunc("PUT /mantenimientos/{id}", func(w http.ResponseWriter, r *http.Request) {
		id, ok := comun.LeerID(r.PathValue("id"))
		if !ok {
			comun.ErrorJSON(w, http.StatusBadRequest, "El id debe ser un número entero positivo")
			return
		}
		var m comun.Mantenimiento
		if !comun.LeerJSON(w, r, &m) {
			return
		}
		m.Limpiar()
		if problema := m.Validar(); problema != "" {
			comun.ErrorJSON(w, http.StatusBadRequest, problema)
			return
		}

		// UPDATE ... RETURNING devuelve la fila ya modificada; si no hay fila, el id no existe
		var actualizado comun.Mantenimiento
		err := db.QueryRowContext(r.Context(),
			`UPDATE public.mantenimientos_mantenimiento
			    SET fecha = $1, descripcion = $2, tecnico = $3
			  WHERE id = $4
			RETURNING id::int, equipo_id, fecha::text, descripcion, tecnico`,
			m.Fecha, m.Descripcion, m.Tecnico, id,
		).Scan(&actualizado.ID, &actualizado.EquipoID, &actualizado.Fecha,
			&actualizado.Descripcion, &actualizado.Tecnico)
		if errors.Is(err, sql.ErrNoRows) {
			comun.ErrorJSON(w, http.StatusNotFound, "No existe un mantenimiento con ese id")
			return
		}
		if err != nil {
			log.Println("actualizar falló:", err)
			if comun.EsErrorDeDatos(err) {
				comun.ErrorJSON(w, http.StatusBadRequest, "Alguno de los datos no es válido")
				return
			}
			comun.ErrorJSON(w, http.StatusInternalServerError, "No se pudo actualizar el mantenimiento")
			return
		}
		comun.Responder(w, http.StatusOK, actualizado)
	})

	comun.Iniciar(mux, "actualizar-go", "8007")
}