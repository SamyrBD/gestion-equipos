// Microservicio de ELIMINACIÓN - Node.js + Express
// Operación: DELETE /mantenimientos/:id
const { pool, crearApp, iniciar, idValido } = require("./comun");

const app = crearApp("eliminar-node");

app.delete("/mantenimientos/:id", async (req, res) => {
  if (!idValido(req.params.id)) {
    return res.status(400).json({ error: "El id debe ser un número entero positivo" });
  }
  const id = Number(req.params.id);

  try {
    const resultado = await pool.query(
      "DELETE FROM public.mantenimientos_mantenimiento WHERE id = $1",
      [id]
    );
    // rowCount = cuántas filas se borraron; 0 significa que ese id no existía
    if (resultado.rowCount === 0) {
      return res.status(404).json({ error: `No existe un mantenimiento con id ${id}` });
    }
    res.json({ eliminado: true, id });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "No se pudo eliminar el mantenimiento" });
  }
});

iniciar(app, "eliminar-node");