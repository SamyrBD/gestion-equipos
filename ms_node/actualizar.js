// Microservicio de ACTUALIZACIÓN - Node.js + Express
// Operación: PUT /mantenimientos/:id
const { pool, crearApp, iniciar, validar, idValido } = require("./comun");

const app = crearApp("actualizar-node");

app.put("/mantenimientos/:id", async (req, res) => {
  if (!idValido(req.params.id)) {
    return res.status(400).json({ error: "El id debe ser un número entero positivo" });
  }
  const id = Number(req.params.id);
  const datos = req.body || {};

  const problema = validar(datos);
  if (problema) return res.status(400).json({ error: problema });

  try {
    // UPDATE ... RETURNING devuelve la fila ya modificada; si no hay fila, el id no existe
    const { rows } = await pool.query(
      `UPDATE public.mantenimientos_mantenimiento
          SET fecha = $1, descripcion = $2, tecnico = $3
        WHERE id = $4
    RETURNING id::int AS id, equipo_id, fecha::text AS fecha, descripcion, tecnico`,
      [datos.fecha, datos.descripcion.trim(), datos.tecnico.trim(), id]
    );
    if (rows.length === 0) {
      return res.status(404).json({ error: `No existe un mantenimiento con id ${id}` });
    }
    res.json(rows[0]);
  } catch (err) {
    console.error(err);
    if (err.code && err.code.startsWith("22")) {
      return res.status(400).json({ error: "Alguno de los datos no es válido" });
    }
    res.status(500).json({ error: "No se pudo actualizar el mantenimiento" });
  }
});

iniciar(app, "actualizar-node");