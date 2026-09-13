// Único dato que sigue siendo mock: CreditWise no tiene fuente en Nessie.
// Todo lo demás del dashboard (saldo, transacciones, bills, ingresos/egresos)
// viene del backend vía lib/api.ts.
export const creditWise = {
  score: 790,
  maxScore: 850,
  label: "Excelente",
  updated: "10 sep 2026",
};
