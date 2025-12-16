#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import struct
import os

PORT = 8888
TOTAL_SIZE = 4096
HEADER_SIZE = 256
DATA_SIZE = TOTAL_SIZE - HEADER_SIZE

block_no = 0


class SimpleHTTP11Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        global block_no

        print(f"GET {self.path} block={block_no}", flush=True)

        # ---- build response ----
        header = bytearray(HEADER_SIZE)
        header[0:4] = struct.pack("<I", block_no)  # block number LE
        payload = os.urandom(DATA_SIZE)

        body = header + payload

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()

        self.wfile.write(body)
        self.wfile.flush()

        block_no += 1
        self.close_connection = True

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            _ = self.rfile.read(length)  # consume payload

        print(f"PUT {self.path} ACK", flush=True)

        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

        self.close_connection = True

    def log_message(self, format, *args):
        # Silence default logging
        return


def main():
    server = HTTPServer(("0.0.0.0", PORT), SimpleHTTP11Handler)
    print(f"HTTP/1.1 test server running on port {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("Server stopped")


if __name__ == "__main__":
    main()
