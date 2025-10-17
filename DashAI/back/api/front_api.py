import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, RedirectResponse
from kink import di, inject

router = APIRouter()


# React router should handle paths under /app, which are defined in index.html
@router.get("/app/{full_path:path}")
@inject
async def read_index(
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    front_build_path = config["FRONT_BUILD_PATH"]
    index_path = Path(f"{front_build_path}/index.html").absolute()
    # Avoids caching of index.html (forces reload of front on every request)
    response = FileResponse(index_path)
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# Serving static files
@router.get("/{file:path}")
@inject
async def serve_files(
    file: str,
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    front_build_path = config["FRONT_BUILD_PATH"]
    try:
        if file == "":
            return RedirectResponse(url="/app/")
        path = Path(f"{front_build_path}/{file}").absolute()
        os.stat(path)
        return FileResponse(path)
    except FileNotFoundError:
        return RedirectResponse(url="/app/")
