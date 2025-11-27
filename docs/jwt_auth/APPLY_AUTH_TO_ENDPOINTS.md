# Cómo Aplicar Autenticación a Endpoints Existentes

## Estado Actual

✅ **El middleware JWT ya está activo** - Todos los endpoints bajo `/api/v1/` requieren autenticación excepto:
- `/api/v1/analytics/health`
- `/docs`
- `/redoc`
- `/`

Esto significa que tus endpoints existentes YA están protegidos. Sin embargo, si quieres:
1. Acceder a la información del usuario autenticado
2. Restringir por roles específicos
3. Implementar lógica basada en el usuario

Sigue estos ejemplos:

## Ejemplo 1: Acceder a Información del Usuario

### Antes (sin información del usuario)

```python
@router.post("/analytics/dashboards", response_model=DashboardResponse)
async def create_dashboard(
    dashboard: DashboardCreate,
    service: DashboardService = Depends(get_dashboard_service)
):
    return await service.create(dashboard)
```

### Después (con información del usuario)

```python
from app.middleware.authentication import get_current_user

@router.post("/analytics/dashboards", response_model=DashboardResponse)
async def create_dashboard(
    dashboard: DashboardCreate,
    user: dict = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    # Ahora puedes usar información del usuario
    logger.info(f"Dashboard created by user: {user['userId']}")

    # Podrías añadir el userId al dashboard
    dashboard_dict = dashboard.model_dump()
    dashboard_dict['created_by'] = user['userId']

    return await service.create(dashboard)
```

## Ejemplo 2: Restringir por Roles

### Solo Administradores Pueden Eliminar

```python
from app.middleware.authentication import require_role

@router.delete("/analytics/dashboards/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: str,
    user: dict = Depends(require_role(["admin"])),  # Solo admin
    service: DashboardService = Depends(get_dashboard_service)
):
    await service.ensure_indexes()
    logger.info(f"Dashboard {dashboard_id} deleted by admin: {user['userId']}")
    return await service.delete(dashboard_id)
```

### Múltiples Roles Permitidos

```python
@router.put("/analytics/dashboards/{dashboard_id}")
async def update_dashboard(
    dashboard_id: str,
    dashboard: DashboardUpdate,
    user: dict = Depends(require_role(["admin", "moderator", "editor"])),
    service: DashboardService = Depends(get_dashboard_service)
):
    await service.ensure_indexes()
    return await service.update(dashboard_id, dashboard)
```

## Ejemplo 3: Lógica Condicional por Rol

```python
from app.middleware.authentication import get_current_user

@router.get("/analytics/dashboards", response_model=List[DashboardResponse])
async def list_dashboards(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    await service.ensure_indexes()

    # Administradores ven todos los dashboards
    if user['role'] == 'admin':
        return await service.get_all(skip=skip, limit=limit)

    # Usuarios regulares solo ven sus propios dashboards
    return await service.get_by_user(user['userId'], skip=skip, limit=limit)
```

## Ejemplo 4: Request State (Alternativa)

Si no quieres usar `Depends()`, puedes acceder al usuario desde `request.state`:

```python
from fastapi import Request

@router.get("/analytics/dashboards/{dashboard_id}")
async def get_dashboard(
    dashboard_id: str,
    request: Request,
    service: DashboardService = Depends(get_dashboard_service)
):
    # Acceder al usuario desde request.state
    user = request.state.user

    logger.info(f"Dashboard {dashboard_id} accessed by {user['userId']}")

    return await service.get_by_id(dashboard_id)
```

## Aplicación a Endpoints Actuales

### Beat Metrics Endpoints

```python
# app/endpoints/beat_metrics.py
from app.middleware.authentication import get_current_user, require_role

# Lectura: Todos los usuarios autenticados
@router.get("/analytics/beat-metrics", response_model=List[BeatMetricsResponse])
async def get_beat_metrics(
    beat_id: Optional[str] = Query(None, alias="beatId"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user: dict = Depends(get_current_user),  # Añadir
    service: BeatMetricsService = Depends(get_beat_metrics_service),
):
    await service.ensure_indexes()
    return await service.get_all(beat_id=beat_id, skip=skip, limit=limit)

# Creación: Todos los usuarios autenticados
@router.post("/analytics/beat-metrics", response_model=BeatMetricsResponse)
async def create_beat_metrics(
    beat_metrics: BeatMetricsCreate,
    user: dict = Depends(get_current_user),  # Añadir
    service: BeatMetricsService = Depends(get_beat_metrics_service)
):
    await service.ensure_indexes()
    return await service.create(beat_metrics)

# Eliminación: Solo administradores
@router.delete("/analytics/beat-metrics/{beat_metrics_id}")
async def delete_beat_metrics(
    beat_metrics_id: str,
    user: dict = Depends(require_role(["admin"])),  # Cambiar
    service: BeatMetricsService = Depends(get_beat_metrics_service)
):
    await service.ensure_indexes()
    return await service.delete(beat_metrics_id)
```

### Dashboard Endpoints

```python
# app/endpoints/dashboards.py
from app.middleware.authentication import get_current_user, require_role

# GET - Todos los usuarios
@router.get("/analytics/dashboards", response_model=List[DashboardResponse])
async def list_dashboards(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user),  # Añadir si necesitas info del usuario
    service: DashboardService = Depends(get_dashboard_service)
):
    await service.ensure_indexes()
    await service.seed_initial()
    return await service.get_all(skip=skip, limit=limit)

# DELETE - Solo administradores
@router.delete("/analytics/dashboards/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: str,
    user: dict = Depends(require_role(["admin"])),  # Cambiar
    service: DashboardService = Depends(get_dashboard_service)
):
    await service.ensure_indexes()
    return await service.delete(dashboard_id)
```

## Añadir Nuevos Endpoints Abiertos

Si quieres que un endpoint NO requiera autenticación, añádelo a `OPEN_PATHS`:

```python
# app/middleware/authentication.py

OPEN_PATHS = [
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/analytics/health",
    "/api/v1/analytics/public-stats",  # Nuevo endpoint público
    "/",
]
```

## Estructura del Objeto User

Cuando uses `get_current_user()` o `require_role()`, recibirás un diccionario con:

```python
user = {
    "userId": "123",              # ID único del usuario
    "email": "user@example.com",  # Email del usuario
    "role": "user",               # Rol: user, admin, moderator, etc.
}
```

## Manejo de Errores

Los helpers ya manejan errores automáticamente:

- **401 Unauthorized**: Sin token o token expirado
- **403 Forbidden**: Token inválido o permisos insuficientes

Si necesitas validación personalizada:

```python
from fastapi import HTTPException, status

@router.delete("/analytics/critical-resource/{resource_id}")
async def delete_critical_resource(
    resource_id: str,
    user: dict = Depends(get_current_user)
):
    # Solo el propietario puede eliminar
    resource = await get_resource(resource_id)
    if resource.owner_id != user['userId']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own resources"
        )

    # Continuar con la lógica...
```

## Testing con Autenticación

### Crear Token JWT para Testing

```python
# tests/conftest.py o tests/test_helpers.py
from jose import jwt
from app.core.config import settings
import time

def create_test_token(user_id: str = "test-123", role: str = "user"):
    """Crear token JWT para testing"""
    payload = {
        "userId": user_id,
        "email": "test@example.com",
        "role": role,
        "exp": int(time.time()) + 3600  # Expira en 1 hora
    }
    return jwt.encode(payload, settings.JWT_SECRET)

### Ejemplo de Test

```python
# tests/test_dashboards.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_dashboard(client: AsyncClient):
    # Crear token de prueba
    token = create_test_token(user_id="test-123", role="user")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/analytics/dashboards",
        json={"name": "Test Dashboard"},
        headers=headers
    )

    assert response.status_code == 201

@pytest.mark.asyncio
async def test_admin_only_endpoint(client: AsyncClient):
    # Test con usuario admin
    admin_token = create_test_token(user_id="admin-123", role="admin")
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = await client.delete(
        "/api/v1/analytics/dashboards/123",
        headers=headers
    )

    assert response.status_code == 200
```

## Resumen

1. ✅ **Todos los endpoints ya están protegidos** por defecto
2. 🔧 **Para acceder a info del usuario**: Usa `Depends(get_current_user)`
3. 🔒 **Para restringir por roles**: Usa `Depends(require_role(["admin"]))`
4. 🎯 **Para endpoints públicos**: Añádelos a `OPEN_PATHS`
5. 📝 **El usuario está en**: `request.state.user` o vía `Depends()`

**¿Necesitas aplicar autenticación ahora?**
- Si no, todo ya funciona con autenticación básica
- Si sí, sigue los ejemplos anteriores según tus necesidades
