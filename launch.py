import subprocess
import sys
import os
import time
import argparse

# Simple launcher: start local file handler, then HTTP server

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_HANDLER = os.path.join(THIS_DIR, "fileHndler.py")
SERVER = os.path.join(THIS_DIR, "server.py")

def parse_args():
    parser = argparse.ArgumentParser(description="Start file handler then HTTP server")
    parser.add_argument("filename", nargs="?", default=os.environ.get("LAUNCH_FILE", "example.bin"),
                        help="File to send (default from LAUNCH_FILE or example.bin)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay (seconds) before starting server")
    return parser.parse_args()

def main():
    args = parse_args()

    print(f"Starting file handler for: {args.filename}")
    fh_proc = subprocess.Popen([sys.executable, FILE_HANDLER, args.filename], cwd=THIS_DIR)

    # Give the handler a moment to bind its socket
    time.sleep(max(0.0, args.delay))

    print("Starting server...")
    srv_proc = subprocess.Popen([sys.executable, SERVER], cwd=THIS_DIR)

    try:
        print("Both processes started. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            if fh_proc.poll() is not None:
                print("File handler exited.")
                break
            if srv_proc.poll() is not None:
                print("Server exited.")
                break
    except KeyboardInterrupt:
        print("\nStopping processes...")
    finally:
        for p in (srv_proc, fh_proc):
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                p.kill()
        print("Stopped.")

if __name__ == "__main__":
    main()