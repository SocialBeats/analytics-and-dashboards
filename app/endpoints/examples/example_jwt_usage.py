"""
Example Protected Endpoints - Demonstrating JWT Authentication Usage

Este archivo muestra diferentes patrones de uso del middleware de autenticación.
NO es necesario para producción, es solo un ejemplo de referencia.
"""

from fastapi import APIRouter, Depends, Request
from app.middleware.authentication import get_current_user, require_role

router = APIRouter()


@router.get("/example/public")
async def public_endpoint():
    """
    Endpoint público sin autenticación
    (Debe estar en OPEN_PATHS del middleware)
    """
    return {
        "message": "This is a public endpoint",
        "authentication": "not required"
    }


@router.get("/example/protected")
async def protected_endpoint(user: dict = Depends(get_current_user)):
    """
    Endpoint protegido - Requiere autenticación pero no roles específicos
    """
    return {
        "message": "Access granted",
        "user": {
            "userId": user["userId"],
            "email": user["email"],
            "role": user["role"]
        }
    }


@router.get("/example/admin")
async def admin_only_endpoint(user: dict = Depends(require_role(["admin"]))):
    """
    Endpoint solo para administradores
    """
    return {
        "message": "Admin access granted",
        "user_id": user["userId"],
        "role": user["role"]
    }


@router.get("/example/editor")
async def editor_endpoint(user: dict = Depends(require_role(["admin", "editor"]))):
    """
    Endpoint para usuarios con rol editor o administradores
    """
    return {
        "message": "Editor access granted",
        "user": {
            "userId": user["userId"],
            "role": user["role"]
        }
    }


@router.get("/example/user-info")
async def get_user_info(request: Request):
    """
    Alternativa: Acceder al usuario desde request.state
    (Sin usar Depends)
    """
    if not hasattr(request.state, "user"):
        return {
            "message": "Not authenticated",
            "user": None
        }

    user = request.state.user
    return {
        "message": "User information",
        "user": {
            "userId": user["userId"],
            "email": user["email"],
            "role": user["role"]
        }
    }


@router.post("/example/create-resource")
async def create_resource(
    data: dict,
    user: dict = Depends(require_role(["admin", "moderator"]))
):
    """
    Ejemplo de endpoint POST protegido con verificación de roles
    """
    return {
        "message": "Resource created successfully",
        "created_by": user["userId"],
        "creator_role": user["role"],
        "data": data
    }
