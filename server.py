#!/usr/bin/python

import socket
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

CHUNK_SIZE = 4096
PORT = 8888

# { trx_id : { "last_chunk": bytes, "awaiting_ack": bool } }
active_transactions = {}
transactions_lock = threading.Lock()


# --------------------------------------------------
# REPLACEMENT: generate random chunk (NO IPC)
# --------------------------------------------------
def get_chunk_from_filehandler():
    # Return exactly CHUNK_SIZE bytes every time
    return os.urandom(CHUNK_SIZE)


class HTTPServerV4(HTTPServer):
    address_family = socket.AF_INET


class RequestHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def do_GET(self):
        print(f"GET from {self.client_address} path={self.path}", flush=True)

        trx_id = self.path.lstrip("/")
        if not trx_id:
            self.send_error(400, "Missing transaction ID")
            return

        with transactions_lock:
            session = active_transactions.get(trx_id)

            if session is None:
                if active_transactions:
                    self.send_error(403, "Another transaction active")
                    self.close_connection = True
                    return

                chunk = get_chunk_from_filehandler()
                active_transactions[trx_id] = {
                    "last_chunk": chunk,
                    "awaiting_ack": True
                }
                print(f"{trx_id}: INIT -> sending first chunk")

            else:
                if session["awaiting_ack"]:
                    chunk = session["last_chunk"]
                    print(f"{trx_id}: REPEAT -> resending last chunk")
                else:
                    chunk = get_chunk_from_filehandler()
                    session["last_chunk"] = chunk
                    session["awaiting_ack"] = True
                    print(f"{trx_id}: ACK'd -> sending next chunk")

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(chunk)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(chunk)
        self.close_connection = True


    def do_PUT(self):
        print(f"PUT from {self.client_address} path={self.path}", flush=True)

        trx_id = self.path.lstrip("/")
        if not trx_id:
            self.send_error(400, "Missing transaction ID")
            self.close_connection = True
            return

        with transactions_lock:
            session = active_transactions.get(trx_id)
            if not session:
                self.send_error(403, "Transaction not active")
                self.close_connection = True
                return

            if not session["awaiting_ack"]:
                print(f"{trx_id}: duplicate ACK")
            else:
                session["awaiting_ack"] = False
                print(f"{trx_id}: ACK received")

        payload = b"ACK"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.close_connection = True


def main():
    httpd = HTTPServerV4(("0.0.0.0", PORT), RequestHandler)
    print(f"HTTP server started on 0.0.0.0:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("HTTP server stopped")


if __name__ == "__main__":
    main()
