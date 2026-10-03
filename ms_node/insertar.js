// Microservicio de INSERCIÓN - Node.js + Express
// Operación: POST /mantenimientos
const { pool, crearApp, iniciar, validar } = require("./comun");

const app = crearApp("insertar-node");

app.post("/mantenimientos", async (req, res) => {
  const datos = req.body || {};

  // 1) Validar ANTES de tocar la base de datos
  if (!Number.isInteger(datos.equipo_id) || datos.equipo_id <= 0) {
    return res.status(400).json({ error: "equipo_id debe ser un número entero positivo" });
  }
  const problema = validar(datos);
  if (problema) return res.status(400).json({ error: problema });

  // 2) Insertar y devolver la fila creada (con su id)
  try {
    const { rows } = await pool.query(
      `INSERT INTO public.mantenimientos_mantenimiento (equipo_id, fecha, descripcion, tecnico)
       VALUES ($1, $2, $3, $4)
       RETURNING id::int AS id, equipo_id, fecha::text AS fecha, descripcion, tecnico`,
      [datos.equipo_id, datos.fecha, datos.descripcion.trim(), datos.tecnico.trim()]
    );
    res.status(201).json(rows[0]);
  } catch (err) {
    console.error(err);
    // Los errores de Postgres que empiezan por "22" son de datos inválidos
    if (err.code && err.code.startsWith("22")) {
      return res.status(400).json({ error: "Alguno de los datos no es válido" });
    }
    res.status(500).json({ error: "No se pudo guardar el mantenimiento" });
  }
});

iniciar(app, "insertar-node");