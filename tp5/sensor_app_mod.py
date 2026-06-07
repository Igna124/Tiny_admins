#!/usr/bin/env python3
import os
import sys
import json
import time
import threading
import random
from http.server import HTTPServer, BaseHTTPRequestHandler

DEVICE_PATH = "/dev/signal_cdd"
HTTP_PORT = 8081  # Cambiado a 8081 para que no choque con el anterior si querés correr ambos
INTERVALO_LECTURA = 1.0   # segundos
MAX_PUNTOS = 120 

SEÑALES = {
    0: {"nombre": "Señal cuadrada (CH1)", "unidad": "V", "escala": 3.3, "offset": 0.0},
    1: {"nombre": "Señal cuadrada (CH2)", "unidad": "V", "escala": 3.3, "offset": 0.0},
}

class EstadoSensor:
    def __init__(self):
        self.lock = threading.Lock()
        self.señal_activa = 0
        self.tiempos = {0: [], 1: []}
        self.valores = {0: [], 1: []}
        self.tiempo_inicio = None

    def agregar_muestra(self, canal, valor_crudo):
        with self.lock:
            if self.tiempo_inicio is None:
                self.tiempo_inicio = time.time()

            config = SEÑALES[canal]
            valor_escalado = (valor_crudo * config["escala"]) + config["offset"]

            t = round(time.time() - self.tiempo_inicio, 1)
            self.tiempos[canal].append(t)
            self.valores[canal].append(valor_escalado)

            if len(self.tiempos[canal]) > MAX_PUNTOS:
                self.tiempos[canal].pop(0)
                self.valores[canal].pop(0)

    def obtener_datos(self):
        with self.lock:
            return {
                "tiempos_ch0": list(self.tiempos[0]),
                "valores_ch0": list(self.valores[0]),
                "tiempos_ch1": list(self.tiempos[1]),
                "valores_ch1": list(self.valores[1]),
                "señal_activa": self.señal_activa,
                "nombre_ch0": SEÑALES[0]["nombre"],
                "nombre_ch1": SEÑALES[1]["nombre"],
                "unidad": SEÑALES[0]["unidad"],
            }

    def cambiar_señal(self, nueva):
        if nueva not in (0, 1):
            return False
        try:
            if os.path.exists(DEVICE_PATH):
                with open(DEVICE_PATH, "w") as f:
                    f.write(str(nueva))
        except Exception as e:
            print(f"Error escribiendo al CDD: {e}")
            return False
        self.señal_activa = nueva
        print(f"[CDD] Señal activa: {nueva} ({SEÑALES[nueva]['nombre']})")
        return True

estado = EstadoSensor()

def hilo_lectura():
    sim_ch0 = 0
    sim_ch1 = 1
    cont = 0
    while True:
        try:
            if os.path.exists(DEVICE_PATH):
                with open(DEVICE_PATH, "r") as f:
                    dato = f.read().strip()
                    valor = int(dato)
                estado.agregar_muestra(estado.señal_activa, valor)
            else:
                # SIMULACIÓN EN PC: CH1 conmuta cada 2s, CH2 cada 3s
                if cont % 2 == 0: sim_ch0 = 1 if sim_ch0 == 0 else 0
                if cont % 3 == 0: sim_ch1 = 1 if sim_ch1 == 0 else 0
                cont += 1
                
                estado.agregar_muestra(0, sim_ch0)
                estado.agregar_muestra(1, sim_ch1)
        except Exception as e:
            print(f"Error leyendo CDD: {e}")
        time.sleep(INTERVALO_LECTURA)

HTML_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Tiny Admins - TP5</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #ffffff; color: #222222; min-height: 100vh; }
        .header { background: #f5f5f7; padding: 20px 30px; border-bottom: 2px solid #e5e5e7; }
        .header h1 { font-size: 1.4em; color: #00C853; }
        .header p { font-size: 0.9em; color: #555555; margin-top: 4px; }
        .container { max-width: 1100px; margin: 0 auto; padding: 20px; }
        .controls { display: flex; gap: 12px; margin-bottom: 20px; align-items: center; }
        .btn { padding: 10px 24px; border: 2px solid #cbd5e1; border-radius: 8px; cursor: pointer; background: #f1f5f9; color: #334155; font-weight: 600; transition: all 0.2s; }
        .btn:hover { background: #e2e8f0; }
        .btn.active-ch0 { background: #2196F3; border-color: #2196F3; color: #fff; } /* Azul */
        .btn.active-ch1 { background: #EF5350; border-color: #EF5350; color: #fff; } /* Rojo */
        .btn.active-both { background: linear-gradient(135deg, #2196F3 0%, #EF5350 100%); border-color: #2196F3; color: #fff; } /* Degradé Azul a Rojo */
        .status { margin-left: auto; padding: 8px 16px; background: #f1f5f9; border-radius: 6px; font-family: monospace; color: #475569; border: 1px solid #cbd5e1; }
        .chart-wrapper { display: flex; flex-direction: column; gap: 20px; }
        .chart-panel { background: #ffffff; border-radius: 12px; padding: 20px; border: 1px solid #e5e5e7; }
        .chart-panel h2 { font-size: 0.95em; color: #555555; margin-bottom: 14px; font-weight: 500; letter-spacing: 0.05em; text-transform: uppercase; }
        .info { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-top: 16px; }
        .info-card { background: #f9f9fb; padding: 14px 18px; border-radius: 8px; border-left: 3px solid #cbd5e1; color: #334155; border: 1px solid #e5e5e7; }
        .info-card div:first-child { font-size: 0.85em; color: #64748b; font-weight: 500; margin-bottom: 4px; }
        .info-card div:last-child { font-size: 1.4em; font-weight: 600; color: #1e293b; }
        .info-card.ch0 { border-left-color: #2196F3; } /* Borde Azul para CH1 */
        .info-card.ch1 { border-left-color: #EF5350; } /* Borde Rojo para CH2 */
        .chart-panel.hidden { display: none; }
    </style>
</head>
<body>
    <div class="header">
        <h1>TP5 — Device Drivers</h1>
        <p>Tiny Admins · Sistemas de Computación · UNC</p>
    </div>
    <div class="container">
        <div class="controls">
            <button class="btn active-ch0" id="btn-ch0" onclick="cambiarVista(0)">Canal 1 (CH1)</button>
            <button class="btn" id="btn-ch1" onclick="cambiarVista(1)">Canal 2 (CH2)</button>
            <button class="btn" id="btn-both" onclick="cambiarVista(2)">Ambos canales</button>
            <div class="status" id="status">Conectando...</div>
        </div>
        <div class="chart-wrapper">
            <div class="chart-panel" id="panel-ch0"><h2>CH1 — Señal cuadrada</h2><canvas id="chart-ch0"></canvas></div>
            <div class="chart-panel hidden" id="panel-ch1"><h2>CH2 — Señal cuadrada</h2><canvas id="chart-ch1"></canvas></div>
            <div class="chart-panel hidden" id="panel-both"><h2>Vista combinada</h2><canvas id="chart-both"></canvas></div>
        </div>
        <div class="info">
            <div class="info-card ch0"><div>CH1 Valor</div><div id="info-valor-ch0">—</div></div>
            <div class="info-card ch1"><div>CH2 Valor</div><div id="info-valor-ch1">—</div></div>
            <div class="info-card ch0"><div>CH1 Muestras</div><div id="info-muestras-ch0">0</div></div>
            <div class="info-card ch1"><div>CH2 Muestras</div><div id="info-muestras-ch1">0</div></div>
        </div>
    </div>
    <script>
    // ---------------------------------------------------------------
    // Colores de las señales
    // ---------------------------------------------------------------
    const COLOR_CH0 = '#2196F3';   // Azul para Canal 1
    const COLOR_CH1 = '#EF5350';   // Rojo para Canal 2
    let vistaActiva = 0; let señalCDD = 0;
    
    function opcionesEjes() { 
        return { 
            responsive: true, 
            scales: { 
                x: { 
                    title: {
                        display: true,
                        text: 'Tiempo [s]',
                        color: '#475569',
                        font: { size: 13, weight: '600' }
                    },
                    grid: { color: '#00000010' }, 
                    ticks: { color: '#475569' } 
                }, 
                y: { 
                    min: -0.5, 
                    max: 4.0, 
                    title: {
                        display: true,
                        text: 'Voltaje [V]',
                        color: '#475569',
                        font: { size: 13, weight: '600' }
                    },
                    grid: { color: '#00000010' }, 
                    ticks: { color: '#475569' } 
                } 
            } 
        }; 
    }
    function makeDataset(label, color) { return { label, data: [], borderColor: color, backgroundColor: color + '33', stepped: 'after', fill: true }; }

    const chartCH0 = new Chart(document.getElementById('chart-ch0').getContext('2d'), { type: 'line', data: { labels: [], datasets: [makeDataset('CH1', COLOR_CH0)] }, options: opcionesEjes() });
    const chartCH1 = new Chart(document.getElementById('chart-ch1').getContext('2d'), { type: 'line', data: { labels: [], datasets: [makeDataset('CH2', COLOR_CH1)] }, options: opcionesEjes() });
    const chartBoth = new Chart(document.getElementById('chart-both').getContext('2d'), { type: 'line', data: { labels: [], datasets: [makeDataset('CH1', COLOR_CH0), makeDataset('CH2', COLOR_CH1)] }, options: opcionesEjes() });

function cambiarVista(num) {
        vistaActiva = num;

        // Ocultar o mostrar los paneles según el botón presionado
        document.getElementById('panel-ch0').classList.toggle('hidden', num !== 0);
        document.getElementById('panel-ch1').classList.toggle('hidden', num !== 1);
        document.getElementById('panel-both').classList.toggle('hidden', num !== 2);

        // Cambiar cuál botón se ve activo (con color)
        document.getElementById('btn-ch0').className = 'btn' + (num === 0 ? ' active-ch0' : '');
        document.getElementById('btn-ch1').className = 'btn' + (num === 1 ? ' active-ch1' : '');
        document.getElementById('btn-both').className = 'btn' + (num === 2 ? ' active-both' : '');

        // Si se elige un canal individual, se le avisa al backend
        if (num === 0 || num === 1) {
            cambiarCanalCDD(num);
        }
    }

    async function cambiarCanalCDD(canal) {
        if (señalCDD === canal) return;
        try { 
            await fetch('/api/cambiar', { 
                method: 'POST', 
                headers: {'Content-Type': 'application/json'}, 
                body: JSON.stringify({señal: canal}) 
            }); 
            señalCDD = canal;
        } catch (err) {
            console.error('Error al cambiar de canal:', err);
        }
    }
    async function actualizarDatos() {
        try {
            const resp = await fetch('/api/datos');
            const d = await resp.json();
            const t0 = d.tiempos_ch0.map(t => t.toFixed(0));
            const t1 = d.tiempos_ch1.map(t => t.toFixed(0));
            chartCH0.data.labels = t0; chartCH0.data.datasets[0].data = d.valores_ch0; chartCH0.update();
            chartCH1.data.labels = t1; chartCH1.data.datasets[0].data = d.valores_ch1; chartCH1.update();
            chartBoth.data.labels = t0.length >= t1.length ? t0 : t1;
            chartBoth.data.datasets[0].data = d.valores_ch0; chartBoth.data.datasets[1].data = d.valores_ch1; chartBoth.update();
            if (d.valores_ch0.length > 0) document.getElementById('info-valor-ch0').textContent = d.valores_ch0[d.valores_ch0.length - 1].toFixed(1) + ' V';
            if (d.valores_ch1.length > 0) document.getElementById('info-valor-ch1').textContent = d.valores_ch1[d.valores_ch1.length - 1].toFixed(1) + ' V';
            document.getElementById('info-muestras-ch0').textContent = d.valores_ch0.length;
            document.getElementById('info-muestras-ch1').textContent = d.valores_ch1.length;
            document.getElementById('status').textContent = 'Conectado';
        } catch (err) { }
    }
    setInterval(actualizarDatos, 1000);
    </script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        elif self.path == '/api/datos':
            datos = estado.obtener_datos()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(datos).encode('utf-8'))

    def do_POST(self):
        if self.path == '/api/cambiar':
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len)
            try:
                data = json.loads(body)
                nueva = int(data.get('señal', 0))
                ok = estado.cambiar_señal(nueva)
                resp = {"ok": ok, "señal_activa": estado.señal_activa}
            except Exception as e: resp = {"ok": False, "error": str(e)}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode('utf-8'))

def main():
    print("=" * 50)
    print("  TP5 - Servidor de SENSADO SIMULADO Multicanal")
    print("=" * 50)
    t = threading.Thread(target=hilo_lectura, daemon=True)
    t.start()
    server = HTTPServer(('127.0.0.1', HTTP_PORT), Handler)
    print(f"[OK] Servidor web en: http://127.0.0.1:{HTTP_PORT}")
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()

if __name__ == "__main__":
    main()