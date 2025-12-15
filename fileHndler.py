import socket
import argparse
import sys
import os

HOST = '127.0.0.1'
PORT = 5000
CHUNK_SIZE = 4 * 1024
HEADER_SIZE = 256
PAYLOAD_SIZE = CHUNK_SIZE - HEADER_SIZE

class FileHdlr:
    def __init__(self, filePath):
        self._path = filePath
        self._f = open(filePath, 'rb')
        self._block_no = 0

    def readChunk(self):
        payload = self._f.read(PAYLOAD_SIZE)
        if not payload:
            return b''  # EOF as empty bytes

        # Build 256-byte header: first 4 bytes = block number, rest zeroes
        block_bytes = self._block_no.to_bytes(4, byteorder='big')
        header = block_bytes + bytes(HEADER_SIZE - 4)

        # Increment block number for next call
        self._block_no += 1

        return header + payload

    def close(self):
        self._f.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", type=str, help="File to serve")
    args = parser.parse_args()

    file_handler = FileHdlr(args.filename)
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((HOST, PORT))
    server_sock.listen(5)
    print("Server listening...")

    try:
        eof_sent = False
        while True:
            conn, addr = server_sock.accept()
            with conn:
                data = conn.recv(1024).strip().lower()
                print(f"Received: {data} from {addr}")
                if data == b"send":
                    if eof_sent:
                        # If we already sent EOF before, just close up!
                        print("EOF already sent, shutting down.")
                        break
                    chunk = file_handler.readChunk()
                    if not chunk:
                        conn.sendall(b"EOF")
                        print("EOF sent, shutting down server.")
                        eof_sent = True
                        break  # after sending EOF, break out and terminate
                    else:
                        conn.sendall(chunk)
                elif data == b"close":
                    file_handler.close()
                    conn.sendall(b"Handler closed.")
                    print("File handler closed and shutting down.")
                    break
                else:
                    conn.sendall(b"Unknown command")
    finally:
        server_sock.close()
        print("Server shutdown.")
