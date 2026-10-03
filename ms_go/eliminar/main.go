// Microservicio de ELIMINACIÓN (respaldo) - Go
// Operación: DELETE /mantenimientos/{id}
package main

import (
	"log"
	"net/http"

	"ms-mantenimientos-go/comun"
)

func main() {
	db := comun.Conectar()
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", comun.Health(db, "eliminar-go"))

	mux.HandleFunc("DELETE /mantenimientos/{id}", func(w http.ResponseWriter, r *http.Request) {
		id, ok := comun.LeerID(r.PathValue("id"))
		if !ok {
			comun.ErrorJSON(w, http.StatusBadRequest, "El id debe ser un número entero positivo")
			return
		}

		resultado, err := db.ExecContext(r.Context(),
			"DELETE FROM public.mantenimientos_mantenimiento WHERE id = $1", id)
		if err != nil {
			log.Println("eliminar falló:", err)
			comun.ErrorJSON(w, http.StatusInternalServerError, "No se pudo eliminar el mantenimiento")
			return
		}
		// RowsAffected = cuántas filas se borraron; 0 significa que ese id no existía
		filas, _ := resultado.RowsAffected()
		if filas == 0 {
			comun.ErrorJSON(w, http.StatusNotFound, "No existe un mantenimiento con ese id")
			return
		}
		comun.Responder(w, http.StatusOK, map[string]any{"eliminado": true, "id": id})
	})

	comun.Iniciar(mux, "eliminar-go", "8008")
}