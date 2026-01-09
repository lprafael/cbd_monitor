ALTER TABLE control_metricas.ifo_historico
ADD COLUMN IF NOT EXISTS cbd_indice numeric(10,4),
ADD COLUMN IF NOT EXISTS cbd_cantidad integer;

COMMENT ON COLUMN control_metricas.ifo_historico.cbd_indice IS 'Índice CBD de la franja (0.0 a 1.0+)';
COMMENT ON COLUMN control_metricas.ifo_historico.cbd_cantidad IS 'Cantidad de buses únicos operando en la franja';
