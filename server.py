import os
from http.server import HTTPServer, BaseHTTPRequestHandler

CHUNK_SIZE = 96 * 1024  # 65536 bytes

class RandomChunkHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        print(f"GET from {self.client_address} path={self.path}", flush=True)
        # Generate a random chunk for each GET
        chunk = os.urandom(CHUNK_SIZE)

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(chunk)))
        self.end_headers()
        self.wfile.write(chunk)

    def do_PUT(self):
        # Accept the PUT, send a simple HTML response (for your Zephyr ACKs)
        print(f"PUT from {self.client_address} path={self.path}", flush=True)
        payload = b"<html><p>Done</p></html>"
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

def run(server_class=HTTPServer, handler_class=RandomChunkHandler, port=8888):
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    print(f"Serving at port {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("\nHTTP server stopped.")

if __name__ == '__main__':
    run()
