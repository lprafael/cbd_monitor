#!/bin/bash
USER="${PREFECT_FLOW_USER:-user}"
WORKING_DIR="/home/user/cbd_monitor/res_120"
PREFECT_API_URL="http://172.16.222.222:4201/api"
CBD_API_URL="http://172.16.222.222:5001"
PYTHON="${PREFECT_PYTHON:-/usr/bin/python3}"
SERVICE_FILE="/etc/systemd/system/prefect-flow-calcular-ifo.service"

if ! id "$USER" &>/dev/null; then
  echo "Error: usuario '$USER' no existe"
  exit 1
fi

if [ ! -f "$WORKING_DIR/flow_calcular_ifo.py" ]; then
  echo "Error: no se encuentra $WORKING_DIR/flow_calcular_ifo.py"
  exit 1
fi

sudo tee "$SERVICE_FILE" << SERVICEEOF
[Unit]
Description=Prefect flow Calcular IFO (8:00)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORKING_DIR
Environment="PREFECT_API_URL=$PREFECT_API_URL"
Environment="CBD_API_URL=$CBD_API_URL"
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=$PYTHON flow_calcular_ifo.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable prefect-flow-calcular-ifo
sudo systemctl restart prefect-flow-calcular-ifo
sudo systemctl status prefect-flow-calcular-ifo --no-pager
