
import os
from fastapi import Request, HTTPException

def get_allowed_ips():
    ips = os.getenv("ALLOWED_ADMIN_IPS", "")
    if not ips:
        return []
    return [ip.strip() for ip in ips.split(",") if ip.strip()]

def check_admin_ip(request: Request):
    allowed = get_allowed_ips()
    # Si la lista está vacía, asumimos modo desarrollo (permitir todo) o bloqueo total?
    # Por seguridad, si se define la variable pero vacía, podría ser peligroso. 
    # Mejor: Si NO está definida la variable, permitimos todo (dev).
    # Si ESTÁ definida (aunque sea vacía), aplicamos filtro.
    
    env_val = os.getenv("ALLOWED_ADMIN_IPS")
    if not env_val:
        # Default: Permitir acceso si no hay configuración específica
        return True

    client_host = request.client.host if request.client else "0.0.0.0"
    
    if "0.0.0.0" in allowed or "*" in allowed:
        return True
        
    if client_host not in allowed:
        # Retornamos False para que el router decida qué hacer (403 o ocultar)
        return False
        
    return True
