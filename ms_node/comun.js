// Código COMPARTIDO por los tres microservicios de Node.js (insertar, actualizar, eliminar).
// Cada microservicio sigue siendo un proceso aparte (su propio archivo y su propio puerto);
// solo reutilizan esta caja de herramientas: conexión, validación y arranque.
const express = require("express");
const { Pool } = require("pg");

// Ajusta estos límites a los max_length de tu modelo Mantenimiento
const MAX_DESCRIPCION = 200;
const MAX_TECNICO = 100;

// Conexión a la base de datos de Supabase (variables de entorno)
const pool = new Pool({
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT) || 5432,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  ssl: process.env.DB_SSL === "false" ? false : { rejectUnauthorized: false },
  max: 2, // pocas conexiones: el plan gratis de Supabase tiene límite y hay varios servicios
});
// Si Supabase cierra una conexión inactiva, el proceso no debe caerse
pool.on("error", (err) => console.error("Error en conexión inactiva:", err.message));

// "2026-02-31" cumple el formato pero NO existe: por eso se comprueba con una fecha real
function fechaValida(texto) {
  if (typeof texto !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(texto)) return false;
  const fecha = new Date(`${texto}T00:00:00Z`);
  return !Number.isNaN(fecha.getTime()) && fecha.toISOString().slice(0, 10) === texto;
}

function textoValido(valor, maximo) {
  return typeof valor === "string" && valor.trim().length > 0 && valor.trim().length <= maximo;
}

// Devuelve un mensaje de error, o null si los datos son correctos
function validar(datos) {
  if (!fechaValida(datos.fecha)) return "fecha debe tener el formato AAAA-MM-DD y ser una fecha real";
  if (!textoValido(datos.descripcion, MAX_DESCRIPCION)) {
    return `descripcion es obligatoria (máximo ${MAX_DESCRIPCION} caracteres)`;
  }
  if (!textoValido(datos.tecnico, MAX_TECNICO)) {
    return `tecnico es obligatorio (máximo ${MAX_TECNICO} caracteres)`;
  }
  return null;
}

// Un id válido es un entero positivo que cabe en la columna (máx. 9 dígitos)
function idValido(texto) {
  return /^\d{1,9}$/.test(texto) && Number(texto) > 0;
}

// Crea la aplicación Express con su GET /health (lo consulta el monitor de gestion_ti)
function crearApp(nombre) {
  const app = express();
  app.use(express.json());
  app.get("/health", async (req, res) => {
    try {
      await pool.query("SELECT 1");
      res.json({ status: "ok", servicio: nombre, lenguaje: "Node.js" });
    } catch (err) {
      res.status(503).json({ status: "error", detalle: err.message });
    }
  });
  return app;
}

// Agrega los manejadores de error y pone el servidor a escuchar
function iniciar(app, nombre) {
  app.use((req, res) => res.status(404).json({ error: "Ruta no encontrada" }));
  // Express reconoce un manejador de errores porque tiene 4 parámetros
  app.use((err, req, res, next) => {
    if (err.type === "entity.parse.failed") {
      return res.status(400).json({ error: "El cuerpo debe ser un JSON válido" });
    }
    console.error(err);
    res.status(500).json({ error: "Error interno del servicio" });
  });
  const puerto = process.env.PORT || 3000;
  const host = process.env.HOST || "127.0.0.1"; // servicio interno: solo gestion_ti lo llama
  app.listen(puerto, host, () => console.log(`${nombre} escuchando en ${host}:${puerto}`));
}

module.exports = { pool, crearApp, iniciar, validar, idValido };