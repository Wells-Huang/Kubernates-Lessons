import json
import os
import socket
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


HOST = "0.0.0.0"
PORT = 8080
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-0.redis-headless.default.svc.cluster.local")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_USERNAME = os.environ.get("REDIS_USERNAME", "default")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
REDIS_CLUSTER_SERVICE = os.environ.get("REDIS_CLUSTER_SERVICE", "redis.default.svc.cluster.local")
POD_NAME = os.environ.get("POD_NAME", socket.gethostname())
POD_NAMESPACE = os.environ.get("POD_NAMESPACE", "default")


def resolve_host(hostname: str) -> list[str]:
    try:
        results = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except OSError as error:
        return [f"dns lookup failed: {error}"]

    addresses = sorted({item[4][0] for item in results})
    return addresses or ["no records"]


class RedisProtocolError(RuntimeError):
    pass


class RedisClient:
    def __init__(self, host: str, port: int, username: str | None, password: str | None) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def execute(self, *parts: str) -> tuple[object, str]:
        with socket.create_connection((self.host, self.port), timeout=5) as connection:
            writer = connection.makefile("wb")
            reader = connection.makefile("rb")

            if self.password:
                if self.username:
                    self._write_command(writer, "AUTH", self.username, self.password)
                else:
                    self._write_command(writer, "AUTH", self.password)
                self._read_response(reader)

            self._write_command(writer, *parts)
            response = self._read_response(reader)
            peer_ip = connection.getpeername()[0]

        return response, peer_ip

    @staticmethod
    def _write_command(writer, *parts: str) -> None:
        payload = [f"*{len(parts)}\r\n".encode("utf-8")]
        for part in parts:
            encoded = part.encode("utf-8")
            payload.append(f"${len(encoded)}\r\n".encode("utf-8"))
            payload.append(encoded + b"\r\n")
        writer.write(b"".join(payload))
        writer.flush()

    @classmethod
    def _read_response(cls, reader):
        prefix = reader.read(1)
        if not prefix:
            raise RedisProtocolError("empty response from redis")

        if prefix == b"+":
            return cls._read_line(reader)
        if prefix == b"-":
            raise RedisProtocolError(cls._read_line(reader))
        if prefix == b":":
            return int(cls._read_line(reader))
        if prefix == b"$":
            length = int(cls._read_line(reader))
            if length == -1:
                return None
            value = reader.read(length)
            reader.read(2)
            return value.decode("utf-8", errors="replace")
        if prefix == b"*":
            length = int(cls._read_line(reader))
            if length == -1:
                return None
            return [cls._read_response(reader) for _ in range(length)]

        raise RedisProtocolError(f"unsupported redis response prefix: {prefix!r}")

    @staticmethod
    def _read_line(reader) -> str:
        line = reader.readline()
        if not line.endswith(b"\r\n"):
            raise RedisProtocolError("malformed redis line response")
        return line[:-2].decode("utf-8", errors="replace")


def redis_client() -> RedisClient:
    username = REDIS_USERNAME or None
    password = REDIS_PASSWORD or None
    return RedisClient(REDIS_HOST, REDIS_PORT, username, password)


def json_response(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/healthz":
            json_response(self, HTTPStatus.OK, {"status": "ok", "pod": POD_NAME})
            return

        if parsed.path == "/":
            json_response(
                self,
                HTTPStatus.OK,
                {
                    "message": "task6 web service is running",
                    "pod": POD_NAME,
                    "namespace": POD_NAMESPACE,
                    "redis_target": REDIS_HOST,
                    "cluster_service_name": REDIS_CLUSTER_SERVICE,
                    "available_endpoints": [
                        "/dns",
                        "/redis/ping",
                        "/redis/set?key=demo&value=hello",
                        "/redis/get?key=demo",
                    ],
                },
            )
            return

        if parsed.path == "/dns":
            json_response(
                self,
                HTTPStatus.OK,
                {
                    "target_host": REDIS_HOST,
                    "target_host_ips": resolve_host(REDIS_HOST),
                    "cluster_service_name": REDIS_CLUSTER_SERVICE,
                    "cluster_service_ips": resolve_host(REDIS_CLUSTER_SERVICE),
                    "explanation": "target_host should resolve to redis-0 specifically, while cluster_service_name resolves to the Service virtual IP.",
                },
            )
            return

        try:
            client = redis_client()
            if parsed.path == "/redis/ping":
                result, peer_ip = client.execute("PING")
                json_response(
                    self,
                    HTTPStatus.OK,
                    {
                        "command": "PING",
                        "result": result,
                        "connected_peer_ip": peer_ip,
                        "redis_target": REDIS_HOST,
                        "resolved_target_ips": resolve_host(REDIS_HOST),
                    },
                )
                return

            if parsed.path == "/redis/set":
                key = query.get("key", ["demo"])[0]
                value = query.get("value", [f"written-by-{POD_NAME}"])[0]
                result, peer_ip = client.execute("SET", key, value)
                json_response(
                    self,
                    HTTPStatus.OK,
                    {
                        "command": "SET",
                        "key": key,
                        "value": value,
                        "result": result,
                        "connected_peer_ip": peer_ip,
                        "redis_target": REDIS_HOST,
                    },
                )
                return

            if parsed.path == "/redis/get":
                key = query.get("key", ["demo"])[0]
                result, peer_ip = client.execute("GET", key)
                json_response(
                    self,
                    HTTPStatus.OK,
                    {
                        "command": "GET",
                        "key": key,
                        "value": result,
                        "connected_peer_ip": peer_ip,
                        "redis_target": REDIS_HOST,
                    },
                )
                return
        except (OSError, RedisProtocolError) as error:
            json_response(
                self,
                HTTPStatus.BAD_GATEWAY,
                {
                    "error": str(error),
                    "redis_target": REDIS_HOST,
                    "resolved_target_ips": resolve_host(REDIS_HOST),
                },
            )
            return

        json_response(self, HTTPStatus.NOT_FOUND, {"error": f"unknown path: {parsed.path}"})

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Server listening on {HOST}:{PORT}")
    server.serve_forever()
