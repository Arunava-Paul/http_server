from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import socket
import threading

CHUNK_SIZE = 4096
IPC_HOST = '127.0.0.1'
IPC_PORT = 5000

# Store state for each transaction: {trx_id: {"last_chunk": ..., "awaiting_ack": bool}}
active_transactions = {}
transactions_lock = threading.Lock()

def get_chunk_from_filehandler():
    with socket.create_connection((IPC_HOST, IPC_PORT), timeout=5) as sock:
        sock.sendall(b"send")
        chunk = sock.recv(CHUNK_SIZE)
        if chunk == b"EOF":
            return None
        return chunk

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        trx_id = self.path.lstrip("/")
        if not trx_id:
            self.send_error(400, "Missing transaction ID in URL")
            return

        with transactions_lock:
            session = active_transactions.get(trx_id)
            if session is None:
                # Only one active session at a time.
                if active_transactions:
                    self.send_error(403, "Another transaction active. Only one allowed at a time.")
                    return
                chunk = get_chunk_from_filehandler()
                if chunk is None:
                    self.send_error(404, f"No more data for transaction ID: {trx_id}")
                    return
                active_transactions[trx_id] = {
                    "last_chunk": chunk,
                    "awaiting_ack": True
                }
                print(f"{trx_id} INIT: sending first chunk, awaiting ACK.")
            else:
                if session["awaiting_ack"]:
                    # Still waiting on ACK for last chunk; resend it.
                    chunk = session["last_chunk"]
                    print(f"{trx_id} REPEAT: still awaiting ACK, resending same chunk.")
                else:
                    # ACK received, send next chunk.
                    chunk = get_chunk_from_filehandler()
                    if chunk is None:
                        self.send_error(404, f"No more data for transaction ID: {trx_id}")
                        del active_transactions[trx_id]
                        print(f"{trx_id}: no more data, transaction removed.")
                        return
                    session["last_chunk"] = chunk
                    session["awaiting_ack"] = True
                    print(f"{trx_id} ACK'd: sending next chunk, awaiting ACK.")

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(chunk)

    def do_PUT(self):
        trx_id = self.path.lstrip("/")
        if not trx_id:
            self.send_error(400, "Missing transaction ID in URL")
            return

        with transactions_lock:
            session = active_transactions.get(trx_id)
            if not session:
                self.send_error(403, f"Transaction ID {trx_id} not active or not recognized.")
                return
            if not session["awaiting_ack"]:
                # Already acked!
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Already acknowledged.")
                print(f"{trx_id}: duplicate ACK received.")
                return
            session["awaiting_ack"] = False
            print(f"{trx_id}: ACK received, ready for next GET.")

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ACK accepted.")

    def log_message(self, format, *args):
        pass  # Silence default logging

if __name__ == "__main__":
     # Bind to all interfaces to avoid 'cannot assign requested address'
    bind_addr = "0.0.0.0"
    server = ThreadingHTTPServer((bind_addr, 8888), SimpleHandler)
    print(f"HTTP server started on {bind_addr}:8888 (use your device IP to access)")
     try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("HTTP server stopped.")
