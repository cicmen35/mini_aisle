from __future__ import annotations

import os

import uvicorn

# Inside a container the API must listen on all interfaces; exposure is controlled by the
# published port (compose binds it to 127.0.0.1) or security groups / NetworkPolicy.
DEFAULT_HOST = "0.0.0.0"  # noqa: S104  # nosec B104


def main() -> None:
    uvicorn.run(
        "patchloop_api.app:create_app_from_env",
        factory=True,
        host=os.environ.get("PATCHLOOP_API_HOST", DEFAULT_HOST),
        port=int(os.environ.get("PATCHLOOP_API_PORT", "8000")),
        proxy_headers=True,
        access_log=True,
    )


if __name__ == "__main__":
    main()
