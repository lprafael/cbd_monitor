# Despliegue del flow Prefect: Calcular IFO con notificación (8:00 AM)

El flow ejecuta **todos los días a las 8:00 AM** el comando:

```bash
python calcular_ifo.py --notificacion
```

(Procesa el día anterior D-1 y envía notificaciones a empresas con incumplimientos.)

---

## Prefect ya instalado

Prefect está disponible en **http://172.16.222.222:4201/dashboard**. Solo hay que apuntar el CLI y el worker a esa API y crear el deployment.

---

## 1. Conectar el CLI al servidor Prefect

En la máquina donde tienes el código `res_120` (por ejemplo el servidor `/home/user/cbd_monitor/res_120`), configura la API de Prefect:

```bash
export PREFECT_API_URL=http://172.16.222.222:4201/api
```

(Para que sea permanente, añade esa línea a `~/.bashrc` o al `.env` del proyecto.)

Si en esa máquina no tienes el CLI de Prefect, instálalo solo para poder crear el deployment:

```bash
pip install "prefect>=2.14"
```

---

## 2. Registrar el deployment y dejar el flow sirviendo (Prefect 3)

En Prefect 3 no se usa `prefect deployment build`. El flow usa **`flow.serve()`** con el schedule ya definido en código (8:00 AM, America/Asuncion).

Desde la carpeta del script:

```bash
export PREFECT_API_URL=http://172.16.222.222:4201/api
cd /home/user/cbd_monitor/res_120
python flow_calcular_ifo.py
```

Ese comando:

1. Registra el deployment **calcular-ifo-diario** en tu Prefect (172.16.222.222:4201).
2. Asocia el cron **8:00 AM** (zona America/Asuncion).
3. **Queda sirviendo**: el mismo proceso actúa como “worker” y ejecutará el flow cuando toque las 8:00.

**Dejar este proceso corriendo** (o configurarlo como servicio systemd para que arranque al inicio). No hace falta correr `prefect worker start` por separado: `python flow_calcular_ifo.py` ya hace de servidor del flow.

Para cambiar la zona horaria, edita `flow_calcular_ifo.py` (busca `America/Asuncion`) y usa por ejemplo `America/Argentina/Buenos_Aires` o `UTC`.

---

## 4. Prueba manual (sin esperar a las 8:00)

```bash
cd /home/user/cbd_monitor/res_120
prefect deployment run 'Calcular IFO con notificación/calcular-ifo-diario'
```

O ejecutar el flow directamente (sin deployment):

```bash
python flow_calcular_ifo.py
```

---

## 5. Resumen de comandos (servidor) — Prefect 3

Prefect ya está en **http://172.16.222.222:4201/dashboard**. Desde la máquina donde está el código:

```bash
export PREFECT_API_URL=http://172.16.222.222:4201/api
cd /home/user/cbd_monitor/res_120
python flow_calcular_ifo.py
```

Dejar ese proceso en ejecución (o configurarlo como servicio). El schedule 8:00 AM ya está definido en el flow; no hace falta usar `prefect deployment build` ni `prefect worker start` por separado.

---

## Variables de entorno

El flow **pasa al subprocess** `CBD_API_URL`: si no está definida en el entorno, usa por defecto `http://172.16.222.222:5001`. Para otro backend, define `CBD_API_URL` antes de arrancar el flow (p. ej. en systemd o en el shell):

```bash
export CBD_API_URL=http://172.16.222.222:5001
python flow_calcular_ifo.py
```

Otras variables que usa `calcular_ifo.py` / `enviar_informe.py` (correo, BD, etc.) deben estar en el entorno o en un `.env` en `res_120`.
