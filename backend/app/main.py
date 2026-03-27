import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .config import settings
from .api.routes import health, geocode, planets, events

FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
)

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
)

# Register routes — must all be added before the static files catch-all mount.
app.include_router(health.router)
app.include_router(geocode.router)
app.include_router(planets.router)
app.include_router(events.router)


@app.get("/")
async def root():
    """Serve frontend index page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.middleware("http")
async def add_cache_control_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith('.js') or path.endswith('.css'):
        response.headers['Cache-Control'] = 'no-cache'
    return response


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
