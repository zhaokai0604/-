"""Pick a free localhost TCP port for backend startup."""

from __future__ import annotations

import argparse
import socket
import sys


def can_bind(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preferred", type=int, default=8000)
    parser.add_argument("--fallback-start", type=int, default=8001)
    parser.add_argument("--fallback-end", type=int, default=8010)
    args = parser.parse_args()

    candidates = [args.preferred, *range(args.fallback_start, args.fallback_end + 1)]
    seen: set[int] = set()
    for port in candidates:
        if port in seen:
            continue
        seen.add(port)
        if can_bind(port):
            print(port)
            return 0
    print("", end="")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
