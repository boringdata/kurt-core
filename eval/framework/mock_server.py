"""Simple HTTP server for serving mock data during eval scenarios.

This server intercepts HTTP requests and serves mock files from eval/mock/
directory instead of making real network calls.
"""

import http.server
import socket
import socketserver
import threading
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


class MockHTTPHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler that serves mock data from files."""

    # Class variable to store mock directory
    mock_dir: Optional[Path] = None

    # Domains to mock (all others will be tunneled through)
    MOCK_DOMAINS = {
        "acme-corp.com",
        "docs.acme-corp.com",
        "competitor-co.com",
    }

    def do_CONNECT(self):  # noqa: N802
        """Handle CONNECT method for HTTPS proxying.

        For mock domains, intercept and serve mock data.
        For all other domains (like api.anthropic.com), establish a real tunnel.
        """
        # Extract the target host from CONNECT request (format: "host:port")
        target = self.path.split(":")[0]

        # Check if this is a mock domain
        if target in self.MOCK_DOMAINS:
            # Mock domain - send 200 and handle subsequent requests
            self.send_response(200, "Connection Established")
            self.end_headers()
            # After this, client will send the actual HTTP request
            # which we'll handle in do_GET/do_POST
        else:
            # Real domain - establish a proper tunnel
            try:
                # Connect to the real server
                remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote_sock.connect(
                    (target, int(self.path.split(":")[1]) if ":" in self.path else 443)
                )

                # Send success response
                self.send_response(200, "Connection Established")
                self.end_headers()

                # Relay data between client and server
                self._tunnel_traffic(self.connection, remote_sock)

            except Exception as e:
                self.send_error(502, f"Proxy connection failed: {e}")

    def _tunnel_traffic(self, client_sock, remote_sock):
        """Relay traffic between client and remote server.

        Args:
            client_sock: Socket connected to the client
            remote_sock: Socket connected to the remote server
        """
        import select

        sockets = [client_sock, remote_sock]
        timeout = 60

        while True:
            try:
                readable, _, exceptional = select.select(sockets, [], sockets, timeout)

                if exceptional:
                    break

                if not readable:
                    break

                for sock in readable:
                    # Read data from one socket
                    data = sock.recv(8192)
                    if not data:
                        return

                    # Send to the other socket
                    if sock is client_sock:
                        remote_sock.sendall(data)
                    else:
                        client_sock.sendall(data)

            except Exception:
                break

        # Close both connections
        try:
            remote_sock.close()
        except Exception:
            pass

    def do_GET(self):  # noqa: N802
        """Handle GET requests by serving mock files."""
        # Parse the incoming URL
        parsed = urlparse(self.path)

        # Extract domain and path from the request
        # The path will be like http://acme-corp.com/sitemap.xml
        # We need to map this to eval/mock/websites/acme-corp/sitemap.xml

        # For proxy requests, the path includes the full URL
        if self.path.startswith("http://") or self.path.startswith("https://"):
            full_url = self.path
            parsed_url = urlparse(full_url)
            domain = parsed_url.netloc
            path = parsed_url.path
        else:
            # Direct request (not through proxy)
            domain = self.headers.get("Host", "")
            path = parsed.path

        # Map domain to mock directory
        mock_file = self._get_mock_file(domain, path)

        if mock_file and mock_file.exists():
            self._serve_mock_file(mock_file)
        else:
            self._send_404(f"No mock data for {domain}{path}")

    def _get_mock_file(self, domain: str, path: str) -> Optional[Path]:
        """Get the mock file for a given domain and path.

        Args:
            domain: Domain name (e.g., 'acme-corp.com')
            path: URL path (e.g., '/sitemap.xml')

        Returns:
            Path to mock file or None
        """
        if not self.mock_dir:
            return None

        # Map domains to directories
        domain_map = {
            "acme-corp.com": "websites/acme-corp",
            "docs.acme-corp.com": "websites/acme-docs",
            "competitor-co.com": "websites/competitor-co",
        }

        dir_path = domain_map.get(domain)
        if not dir_path:
            return None

        mock_site_dir = self.mock_dir / dir_path

        # Map URL paths to files
        # /sitemap.xml -> sitemap.xml
        # /home -> home.md
        # /blog/how-to-build-scalable-apis -> blog-post-1.md

        if path == "/sitemap.xml":
            return mock_site_dir / "sitemap.xml"

        # Blog post mappings
        blog_mappings = {
            "/blog/how-to-build-scalable-apis": "blog-post-1.md",
            "/blog/announcing-acme-2-0": "blog-post-2.md",
            "/blog/10-tips-for-developer-experience": "blog-post-3.md",
        }

        if path in blog_mappings:
            return mock_site_dir / blog_mappings[path]

        # Direct mappings (e.g., /home -> home.md)
        path_clean = path.strip("/")
        if path_clean:
            md_file = mock_site_dir / f"{path_clean}.md"
            if md_file.exists():
                return md_file
            xml_file = mock_site_dir / f"{path_clean}.xml"
            if xml_file.exists():
                return xml_file

        return None

    def _serve_mock_file(self, file_path: Path):
        """Serve a mock file with appropriate headers.

        Args:
            file_path: Path to the mock file
        """
        content = file_path.read_bytes()

        # Determine content type
        if file_path.suffix == ".xml":
            content_type = "application/xml"
        elif file_path.suffix == ".json":
            content_type = "application/json"
        elif file_path.suffix == ".md":
            # Serve markdown as HTML so trafilatura can extract content
            # Wrap markdown in minimal HTML structure
            md_text = content.decode("utf-8")
            html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Mock Content</title></head>
<body>
<pre>{md_text}</pre>
</body>
</html>"""
            content = html_content.encode("utf-8")
            content_type = "text/html; charset=utf-8"
        else:
            content_type = "text/html"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Mock-Source", str(file_path))
        self.end_headers()
        self.wfile.write(content)

    def _send_404(self, message: str):
        """Send a 404 response.

        Args:
            message: Error message
        """
        content = f"Mock data not found: {message}".encode()
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        """Override to reduce noise in logs."""
        # Only log if verbose
        pass


class MockHTTPServer:
    """HTTP server that serves mock data for testing."""

    def __init__(self, mock_dir: Path, port: int = 8765):
        """Initialize mock HTTP server.

        Args:
            mock_dir: Directory containing mock data
            port: Port to listen on (default: 8765)
        """
        self.mock_dir = Path(mock_dir)
        self.port = port
        self.server: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None

        # Set the mock directory for the handler class
        MockHTTPHandler.mock_dir = self.mock_dir

    def start(self):
        """Start the HTTP server in a background thread."""
        if self.server:
            return  # Already started

        # Create server with SO_REUSEADDR enabled
        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("127.0.0.1", self.port), MockHTTPHandler)

        # Start in background thread
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        print(f"✅ Mock HTTP server started on http://127.0.0.1:{self.port}")

    def stop(self):
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            print("✅ Mock HTTP server stopped")

    def get_proxy_env(self) -> dict:
        """Get environment variables for using this server as proxy.

        Returns:
            Dict with HTTP_PROXY and HTTPS_PROXY settings
        """
        proxy_url = f"http://127.0.0.1:{self.port}"
        return {
            "HTTP_PROXY": proxy_url,
            "HTTPS_PROXY": proxy_url,
            "http_proxy": proxy_url,
            "https_proxy": proxy_url,
        }


def create_mock_server(mock_dir: Optional[Path] = None, port: int = 8765) -> MockHTTPServer:
    """Create a mock HTTP server with default mock directory.

    Args:
        mock_dir: Optional custom mock directory. Defaults to eval/mock/
        port: Port to listen on (default: 8765)

    Returns:
        Configured MockHTTPServer instance
    """
    if mock_dir is None:
        # Default to eval/mock relative to this file
        mock_dir = Path(__file__).parent.parent / "mock"

    return MockHTTPServer(mock_dir, port)
