import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.routes.autoservicio import router as autoservicio_router
from app.routes.admin import router as admin_router

load_dotenv()

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "CAMBIA_ESTO_POR_UNA_CLAVE_LARGA"),
    same_site="lax",
)

# Configurar templates globales
templates = Jinja2Templates(directory="app/templates")

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

app.include_router(autoservicio_router)
app.include_router(admin_router, prefix=os.getenv("ADMIN_ROUTE_PREFIX", ""))
