#!/usr/bin/python

import socket
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

CHUNK_SIZE = 4096
IPC_HOST = '127.0.0.1'
IPC_PORT = 5000
PORT = 8888

# { trx_id : { "last_chunk": bytes, "awaiting_ack": bool } }
active_transactions = {}


def get_chunk_from_filehandler():
    with socket.create_connection((IPC_HOST, IPC_PORT), timeout=5) as sock:
        sock.sendall(b"send")
        chunk = sock.recv(CHUNK_SIZE)
        if not chunk:
            return None
        elif chunk == b"EOF":
            return None
        return chunk


class HTTPServerV4(ThreadingHTTPServer):
    address_family = socket.AF_INET


class RequestHandler(BaseHTTPRequestHandler):

    # ---------------- GET = DATA ----------------
    def do_GET(self):
        print(f"GET from {self.client_address} path={self.path}", flush=True)

        trx_id = self.path.lstrip("/")
        if not trx_id:
            self.send_error(400, "Missing transaction ID")
            return

        session = active_transactions.get(trx_id)

        # ---- New transaction ----
        if session is None:
            if active_transactions:
                self.send_error(403, "Another transaction active")
                return

            chunk = get_chunk_from_filehandler()
            if chunk is None:
                self.send_error(404, "No more data")
                return

            active_transactions[trx_id] = {
                "last_chunk": chunk,
                "awaiting_ack": True
            }
            print(f"{trx_id}: INIT -> sending first chunk")

        # ---- Existing transaction ----
        else:
            if session["awaiting_ack"]:
                chunk = session["last_chunk"]
                print(f"{trx_id}: REPEAT -> resending last chunk")
            else:
                chunk = get_chunk_from_filehandler()
                if chunk is None:
                    del active_transactions[trx_id]
                    self.send_error(404, "No more data")
                    return

                session["last_chunk"] = chunk
                session["awaiting_ack"] = True
                print(f"{trx_id}: ACK'd -> sending next chunk")

        # ---- HTTP response ----
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        print(f"DEBUG: chunk len = {len(chunk)}", flush=True)
        self.send_header("Content-Length", str(len(chunk)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(chunk)
        self.wfile.flush()
        self.close_connection = True

    # ---------------- PUT = ACK ----------------
    def do_PUT(self):
        print(f"PUT from {self.client_address} path={self.path}", flush=True)

        trx_id = self.path.lstrip("/")
        if not trx_id:
            self.send_error(400, "Missing transaction ID")
            return

        session = active_transactions.get(trx_id)
        if not session:
            self.send_error(403, "Transaction not active")
            return

        if not session["awaiting_ack"]:
            # Duplicate ACK
            print(f"{trx_id}: duplicate ACK")
            self._put_response()
            return

        session["awaiting_ack"] = False
        print(f"{trx_id}: ACK received")

        self._put_response()

    # ---------------- Helpers ----------------
    def _put_response(self):
        payload = b"<html><p>Done</p></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()
        self.close_connection = True


def main():
    httpd = HTTPServerV4(("0.0.0.0", PORT), RequestHandler)
    print("Serving at port", PORT)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("HTTP server stopped")


if __name__ == '__main__':
    main()
