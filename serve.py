#!/usr/bin/env python3
"""Serve the static wwwroot site."""

from __future__ import annotations

import argparse
import http.server
import socket
import socketserver
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DIR = ROOT / "wwwroot"


class StaticHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript",
    }


class ReuseTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def local_ipv4_addresses() -> list[str]:
    addresses: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addresses.add(info[4][0])
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("1.1.1.1", 80))
            addresses.add(sock.getsockname()[0])
    except OSError:
        pass
    return sorted(addresses)


def serve_urls(host: str, port: int) -> list[str]:
    if host in ("", "0.0.0.0"):
        urls = [f"http://127.0.0.1:{port}"]
        for address in local_ipv4_addresses():
            if address != "127.0.0.1":
                urls.append(f"http://{address}:{port}")
        return urls
    display_host = host if ":" not in host else f"[{host}]"
    return [f"http://{display_host}:{port}"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve CNC Research Project static site")
    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        default=DEFAULT_DIR,
        help=f"Directory to serve (default: {DEFAULT_DIR.relative_to(ROOT)})",
    )
    parser.add_argument("-p", "--port", type=int, default=8080)
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Address to bind (default: 0.0.0.0 — all network interfaces)",
    )
    parser.add_argument(
        "-l",
        "--localhost-only",
        action="store_true",
        help="Listen on 127.0.0.1 only (not reachable from other devices)",
    )
    args = parser.parse_args()

    host = "127.0.0.1" if args.localhost_only else args.host
    directory = args.directory.resolve()
    if not directory.is_dir():
        raise SystemExit(f"Directory not found: {directory}")

    handler = lambda *h_args, **h_kwargs: StaticHandler(  # noqa: E731
        *h_args, directory=str(directory), **h_kwargs
    )

    with ReuseTCPServer((host, args.port), handler) as httpd:
        print(f"Serving {directory}")
        if host in ("", "0.0.0.0"):
            print("Listening on all network interfaces")
        else:
            print(f"Listening on {host}")
        print("Open:")
        for url in serve_urls(host, args.port):
            print(f"  {url}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
