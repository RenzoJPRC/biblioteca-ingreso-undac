from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import SessionLocal
from app.services.ingreso import registrar_ingreso

from sqlalchemy import text

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/piso/{piso}", response_class=HTMLResponse)
def pantalla_piso(request: Request, piso: int):
    if piso not in (1, 2, 3):
        return HTMLResponse("Piso inválido", status_code=400)
    
    # --- STICKY SESSION LOGIC ---
    locked_floor = request.session.get("kiosk_floor")
    
    if locked_floor:
        # Si ya esta bloqueado en un piso y tratan de ir a otro -> Redirigir al bloqueado
        if int(locked_floor) != piso:
            return RedirectResponse(url=f"/piso/{locked_floor}")
    else:
        # Si no esta bloqueado -> Bloquear en este piso
        request.session["kiosk_floor"] = piso
    
    return templates.TemplateResponse("piso.html", {"request": request, "piso": piso})

@router.post("/api/ingreso")
def api_ingreso(payload: dict):
    piso = int(payload.get("piso", 0))
    codigo = str(payload.get("codigo", "")).strip()

    if piso not in (1, 2, 3):
        return JSONResponse({"ok": False, "mensaje": "Piso inválido"}, status_code=400)

    db = SessionLocal()
    try:
        return registrar_ingreso(db, piso, codigo)
    finally:
        db.close()


@router.get("/api/contador")
def api_contador(hoy: int = 1, piso: int = 0):
    db = SessionLocal()
    try:
        if piso in (1,2,3):
            q = text("""
                SELECT COUNT(*) AS total
                FROM INGRESO
                WHERE fecha = CAST(GETDATE() AS DATE)
                  AND piso = :piso
            """)
            total = db.execute(q, {"piso": piso}).scalar_one()
        else:
            q = text("""
                SELECT COUNT(*) AS total
                FROM INGRESO
                WHERE fecha = CAST(GETDATE() AS DATE)
            """)
            total = db.execute(q).scalar_one()

        return {"ok": True, "total": int(total)}
    finally:
        db.close()
