import http.server
import json
import os

DEVICE_PATH = "/dev/signal_sensors"

class MinimalSensorServer(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):

        if self.path =='/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return

        if self.path =='/data':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            try:
                with open(DEVICE_PATH, 'r') as f:
                    value = f.read().strip()
                response = {"value": int(value)}
            except Exception as e:
                response = {"error": str(e), "value": 0}

            self.wfile.write(json.dumps(response).encode('utf-8'))

        elif self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            with open('index.html', 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File Not Found")
    
    def do_POST(self):

        if self.path == '/change':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data)
            target_signal = str(data.get('signal', '1'))

            try:
                with open(DEVICE_PATH, 'w') as f:
                    f.write(target_signal)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "signal": target_signal}).encode('utf-8'))
            except Exception as e:
                self.send_error(500, str(e))

if __name__ == '__main__':

    if not os.path.exists(DEVICE_PATH):
        print(f"Warning: {DEVICE_PATH} not found. Verify module.")

    server_address = ('0.0.0.0', 5000)
    httpd = http.server.HTTPServer(server_address, MinimalSensorServer)
    print("Server running on http://localhost:5000")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")