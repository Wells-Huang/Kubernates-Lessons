import json
import os
import ssl
import sys
import urllib.error
import urllib.request


TOKEN_FILE = os.environ.get("K8S_TOKEN_FILE", "/var/run/secrets/pod-reader/token")
CA_FILE = os.environ.get("K8S_CA_FILE", "/var/run/secrets/pod-reader/ca.crt")
TARGET_NAMESPACE = os.environ.get("TARGET_NAMESPACE", "default")


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return file.read().strip()


def build_api_url() -> str:
    host = os.environ.get("KUBERNETES_SERVICE_HOST")
    port = os.environ.get("KUBERNETES_SERVICE_PORT_HTTPS", "443")
    if not host:
        raise RuntimeError("KUBERNETES_SERVICE_HOST is not set")
    return f"https://{host}:{port}/api/v1/namespaces/{TARGET_NAMESPACE}/pods"


def fetch_pods() -> list[str]:
    token = read_file(TOKEN_FILE)
    url = build_api_url()
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )

    ssl_context = ssl.create_default_context(cafile=CA_FILE)

    with urllib.request.urlopen(request, context=ssl_context, timeout=10) as response:
        payload = json.load(response)

    return [item["metadata"]["name"] for item in payload.get("items", [])]


def main() -> int:
    try:
        pod_names = fetch_pods()
    except FileNotFoundError as error:
        print(f"failed to read projected service account files: {error}", file=sys.stderr)
        return 1
    except urllib.error.HTTPError as error:
        print(f"kubernetes api returned HTTP {error.code}: {error.reason}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"failed to fetch pods from kubernetes api: {error}", file=sys.stderr)
        return 1

    print(f"pod list in {TARGET_NAMESPACE} namespace:")
    if not pod_names:
        print("(no pods found)")
        return 0

    for index, name in enumerate(pod_names, start=1):
        print(f"{index}. {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
