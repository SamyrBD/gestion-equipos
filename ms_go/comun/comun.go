// Paquete comun: la "caja de herramientas" que comparten los cuatro microservicios en Go
// (consulta, insertar, actualizar, eliminar): conexión, respuestas JSON, validación y arranque.
// Cada microservicio sigue siendo un programa aparte con su propio puerto.
package comun

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/lib/pq"
)

// Ajusta estos límites a los max_length de tu modelo Mantenimiento
const (
	MaxDescripcion = 200
	MaxTecnico     = 100
)

// Mantenimiento es la forma del JSON que entra y sale (el "contrato" común a todos los lenguajes)
type Mantenimiento struct {
	ID          int    `json:"id"`
	EquipoID    int    `json:"equipo_id"`
	Fecha       string `json:"fecha"`
	Descripcion string `json:"descripcion"`
	Tecnico     string `json:"tecnico"`
}

// Env lee una variable de entorno; si está vacía devuelve el valor por defecto
func Env(nombre, porDefecto string) string {
	if valor := os.Getenv(nombre); valor != "" {
		return valor
	}
	return porDefecto
}

// Conectar prepara la conexión a Supabase con las variables DB_*.
// sql.Open no conecta todavía: la conexión real ocurre en la primera consulta.
func Conectar() *sql.DB {
	direccion := url.URL{
		Scheme:   "postgres",
		User:     url.UserPassword(os.Getenv("DB_USER"), os.Getenv("DB_PASSWORD")),
		Host:     Env("DB_HOST", "localhost") + ":" + Env("DB_PORT", "5432"),
		Path:     "/" + Env("DB_NAME", "postgres"),
		RawQuery: "sslmode=" + Env("DB_SSLMODE", "require"),
	}
	db, err := sql.Open("postgres", direccion.String())
	if err != nil {
		log.Fatal("No se pudo preparar la conexión a la base de datos: ", err)
	}
	db.SetMaxOpenConns(2) // pocas conexiones: el plan gratis de Supabase tiene límite
	db.SetMaxIdleConns(1)
	db.SetConnMaxLifetime(5 * time.Minute)
	return db
}

// Responder escribe una respuesta JSON con el código HTTP indicado
func Responder(w http.ResponseWriter, codigo int, datos any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(codigo)
	json.NewEncoder(w).Encode(datos)
}

// ErrorJSON responde {"error": "mensaje"} con el código indicado
func ErrorJSON(w http.ResponseWriter, codigo int, mensaje string) {
	Responder(w, codigo, map[string]string{"error": mensaje})
}

// Health devuelve el manejador de GET /health (lo consulta el monitor de gestion_ti).
// Un servicio está "sano" solo si también puede hablar con la base de datos.
func Health(db *sql.DB, nombre string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ctx, cancelar := context.WithTimeout(r.Context(), 3*time.Second)
		defer cancelar()
		if err := db.PingContext(ctx); err != nil {
			log.Println("health falló:", err)
			Responder(w, http.StatusServiceUnavailable, map[string]string{"status": "error"})
			return
		}
		Responder(w, http.StatusOK, map[string]string{"status": "ok", "servicio": nombre, "lenguaje": "Go"})
	}
}

// LeerID convierte "7" en 7. Solo acepta enteros positivos que caben en la columna id.
func LeerID(texto string) (int, bool) {
	n, err := strconv.Atoi(texto)
	if err != nil || n <= 0 || n > 2147483647 {
		return 0, false
	}
	return n, true
}

// LeerJSON lee el cuerpo de la petición dentro de "destino". Si es inválido, ya responde 400.
func LeerJSON(w http.ResponseWriter, r *http.Request, destino any) bool {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20) // máximo 1 MB
	if err := json.NewDecoder(r.Body).Decode(destino); err != nil {
		ErrorJSON(w, http.StatusBadRequest, "El cuerpo debe ser un JSON válido con los campos correctos")
		return false
	}
	return true
}

// Limpiar quita los espacios sobrantes de los textos
func (m *Mantenimiento) Limpiar() {
	m.Descripcion = strings.TrimSpace(m.Descripcion)
	m.Tecnico = strings.TrimSpace(m.Tecnico)
}

// Validar devuelve un mensaje de error, o "" si los datos son correctos.
// time.Parse rechaza fechas que no existen (por ejemplo 2026-02-31).
func (m *Mantenimiento) Validar() string {
	if _, err := time.Parse("2006-01-02", m.Fecha); err != nil {
		return "fecha debe tener el formato AAAA-MM-DD y ser una fecha real"
	}
	if n := utf8.RuneCountInString(m.Descripcion); n == 0 || n > MaxDescripcion {
		return fmt.Sprintf("descripcion es obligatoria (máximo %d caracteres)", MaxDescripcion)
	}
	if n := utf8.RuneCountInString(m.Tecnico); n == 0 || n > MaxTecnico {
		return fmt.Sprintf("tecnico es obligatorio (máximo %d caracteres)", MaxTecnico)
	}
	return ""
}

// EsErrorDeDatos es verdadero cuando Postgres rechaza un dato (códigos que empiezan por "22")
func EsErrorDeDatos(err error) bool {
	var errPG *pq.Error
	return errors.As(err, &errPG) && strings.HasPrefix(string(errPG.Code), "22")
}

// Iniciar pone el servidor a escuchar. Solo accesible desde dentro del contenedor (127.0.0.1).
func Iniciar(mux *http.ServeMux, nombre, puertoPorDefecto string) {
	direccion := Env("HOST", "127.0.0.1") + ":" + Env("PORT", puertoPorDefecto)
	servidor := &http.Server{
		Addr:              direccion,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      20 * time.Second,
	}
	log.Printf("%s escuchando en %s", nombre, direccion)
	log.Fatal(servidor.ListenAndServe())
}