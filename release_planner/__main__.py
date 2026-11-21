import argparse
import sys

from .server import make_server


def main(argv=None):
    ap = argparse.ArgumentParser(prog="release_planner")
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)
    if not 0 <= args.port <= 65535:
        ap.error("--port must be between 0 and 65535")
    srv = make_server(args.data_dir, args.port)
    print(f"Listening on http://127.0.0.1:{srv.server_address[1]}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
