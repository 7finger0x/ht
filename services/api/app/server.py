from __future__ import annotations

import uvicorn

from .config import settings


if __name__ == "__main__":
    host, port = settings.api_bind.split(":", maxsplit=1)
    uvicorn.run("app.main:app", host=host, port=int(port), reload=settings.api_reload)
