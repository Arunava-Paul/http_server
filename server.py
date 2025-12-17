#!/usr/bin/python

import socket
from http.server import ThreadingHTTPServer
from http.server import SimpleHTTPRequestHandler
import threading

CHUNK_SIZE = 4096
IPC_HOST = '127.0.0.1'
IPC_PORT = 5000
PORT = 8888

# { trx_id : { "last_chunk": bytes, "awaiting_ack": bool } }
active_transactions = {}
transactions_lock = threading.Lock()

def get_chunk_from_filehandler():
    with socket.create_connection((IPC_HOST, IPC_PORT), timeout=5) as sock:
        sock.sendall(b"send")
        chunk = sock.recv(CHUNK_SIZE)
        if chunk == b"EOF":
            return None
        return chunk


class HTTPServerV4(ThreadingHTTPServer):
    address_family = socket.AF_INET

class RequestHandler(SimpleHTTPRequestHandler):
    length = 0
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
            
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(chunk)))
        self.end_headers()
        self.wfile.write(chunk) 
                
        
    def do_PUT(self):
        print(f"PUT from {self.client_address} path={self.path}", flush=True)

        trx_id = self.path.lstrip("/")
        if not trx_id:
            self.send_error(400, "Missing transaction ID")
            return

        with transactions_lock:
            session = active_transactions.get(trx_id)
            if not session:
                self.send_error(403, "Transaction not active")
                
                return

            if not session["awaiting_ack"]:
                # Duplicate ACK
                self._put_response()
                print(f"{trx_id}: duplicate ACK")
                return

            session["awaiting_ack"] = False
            print(f"{trx_id}: ACK received")

        # ---- HTTP response (NO BODY) ----
        self._put_response()
    
    def _put_response(self):
        payload = b"<html><p>Done</p></html>"
        self.length = len(payload)
        self._set_headers()
        self.wfile.write(payload)
        
        
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(self.length))
        self.end_headers()

    def do_POST(self):
        payload = b"<html><p>Done</p></html>"
        self.length = len(payload)
        self._set_headers()
        self.wfile.write(payload)

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
