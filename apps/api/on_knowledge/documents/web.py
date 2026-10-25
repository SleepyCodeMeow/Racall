"""Public HTTP(S) fetching with DNS pinning, redirect and response-size limits."""

import http.client
import ipaddress
import re
import socket
import ssl
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .models import MAX_BYTES


def public_addresses(host: str, port: int) -> list[str]:
    addresses = list({info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("URL должен вести на публичный сайт; локальные адреса запрещены")
    return addresses


def fetch_url(url: str) -> tuple[str, str]:
    """Pin a validated DNS address for the actual socket, including redirects (no rebinding)."""
    for _ in range(5):
        parsed = urlsplit(url)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Допустим только публичный HTTP(S) URL без пароля")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port not in (80, 443):
            raise ValueError("URL должен использовать порт 80 или 443")
        addresses = public_addresses(parsed.hostname, port)
        connection = http.client.HTTPConnection(parsed.hostname, port, timeout=20)
        sock = socket.create_connection((addresses[0], port), timeout=20)
        if parsed.scheme == "https":
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=parsed.hostname)
        connection.sock = sock
        try:
            connection.request(
                "GET",
                (parsed.path or "/") + ("?" + parsed.query if parsed.query else ""),
                headers={"User-Agent": "OpenNotebook/0.1", "Accept-Encoding": "identity"},
            )
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                url = urljoin(url, response.getheader("Location", ""))
                continue
            if response.status != 200:
                raise ValueError(f"Сайт вернул HTTP {response.status}")
            content_type = response.getheader("Content-Type", "").lower()
            if not any(t in content_type for t in ("text/html", "text/plain", "application/xhtml")):
                raise ValueError("URL должен возвращать HTML или текст")
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("Страница превышает 25 МБ")
            soup = BeautifulSoup(data, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "iframe", "form"]):
                tag.decompose()
            title = soup.title.get_text(strip=True) if soup.title else parsed.hostname
            for tag in soup.find_all(re.compile(r"^h[1-6]$")):
                tag.replace_with("\n" + "#" * int(tag.name[1]) + " " + tag.get_text(" ", strip=True) + "\n")
            return title, soup.get_text("\n", strip=True)
        finally:
            connection.close()
    raise ValueError("Слишком много перенаправлений")
