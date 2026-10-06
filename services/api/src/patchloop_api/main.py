from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "patchloop_api.app:create_app_from_env",
        factory=True,
        host=os.environ.get("PATCHLOOP_API_HOST", "0.0.0.0"),  # noqa: S104  # nosec B104 - container
        port=int(os.environ.get("PATCHLOOP_API_PORT", "8000")),
        proxy_headers=True,
        access_log=True,
    )


if __name__ == "__main__":
    main()
