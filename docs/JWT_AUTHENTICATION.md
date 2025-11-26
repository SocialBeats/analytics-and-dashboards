# JWT Authentication Middleware

## Descripción

Este microservicio implementa un middleware de autenticación JWT que valida tokens directamente desde el header `Authorization`.

El middleware intercepta todas las peticiones HTTP y verifica que contengan un token JWT válido antes de permitir el acceso a los endpoints protegidos.

## Configuración

### Variables de Entorno

Configura las siguientes variables en tu archivo `.env`:

```bash
# JWT_SECRET: Clave secreta para verificar tokens JWT
# DEBE ser la misma que usa el servicio de autenticación
JWT_SECRET="your-jwt-secret-key-here-change-in-production"
```

⚠️ **CRÍTICO**: El `JWT_SECRET` debe ser **idéntico** al usado en el servicio que genera los tokens (ej: servicio de autenticación).

## Rutas Abiertas (Sin Autenticación)

Las siguientes rutas **NO** requieren autenticación:

- `/` - Root endpoint
- `/docs` - Swagger UI
- `/redoc` - ReDoc UI
- `/openapi.json` - OpenAPI schema
- `/api/v1/analytics/health` - Health check

Todas las demás rutas bajo `/api/v1/` **requieren autenticación**.

## Cómo Funciona

### 1. Request con Token JWT

El cliente debe enviar el token JWT en el header `Authorization`:

```http
GET /api/v1/analytics/dashboards
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2. Validación del Middleware

El middleware:
1. ✅ Verifica que el header `Authorization` existe
2. ✅ Verifica el formato `Bearer <token>`
3. ✅ Verifica la firma del token con `JWT_SECRET`
4. ✅ Verifica que el token no ha expirado
5. ✅ Extrae la información del usuario del token
6. ✅ Añade la información al `request.state.user`

### 3. Token Válido

Si el token es válido, el request continúa y `request.state.user` contiene:

```python
{
    "userId": "123",              # ID del usuario
    "email": "user@example.com",  # Email
    "role": "user"                # Rol (user, admin, etc.)
}
```

## Uso en Endpoints

### Opción 1: Dependency con `get_current_user`

```python
from fastapi import APIRouter, Depends
from app.middleware.authentication import get_current_user

router = APIRouter()

@router.get("/analytics/dashboards")
async def list_dashboards(user: dict = Depends(get_current_user)):
    # El usuario ya está autenticado
    print(f"User ID: {user['userId']}")
    print(f"Role: {user['role']}")
    return {"dashboards": [...]}
```

### Opción 2: Verificación de Roles

```python
from app.middleware.authentication import require_role

@router.delete("/analytics/dashboards/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: str,
    user: dict = Depends(require_role(["admin"]))  # Solo admin
):
    # Solo usuarios con rol "admin" pueden acceder
    return {"message": "Deleted"}

@router.post("/analytics/premium-feature")
async def premium_feature(
    user: dict = Depends(require_role(["admin", "pro"]))  # Admin o Pro
):
    # Múltiples roles permitidos
    return {"data": [...]}
```

### Opción 3: Acceso desde Request

```python
from fastapi import Request

@router.get("/analytics/profile")
async def get_profile(request: Request):
    user = request.state.user
    return {
        "userId": user["userId"],
        "email": user["email"],
        "role": user["role"]
    }
```

## Respuestas de Error

### 400 Bad Request
Falta la versión de API en la ruta:
```json
{
  "detail": "You must specify the API version, e.g. /api/v1/..."
}
```

### 401 Unauthorized
Sin token o token expirado:
```json
{
  "detail": "Missing token"
}
```

```json
{
  "detail": "Token expired. Please login again."
}
```

### 403 Forbidden
Token inválido o permisos insuficientes:
```json
{
  "detail": "Invalid or expired token"
}
```

```json
{
  "detail": "Insufficient permissions. Required roles: admin"
}
```

## Testing

### Ejemplo con cURL

```bash
# 1. Obtener token del servicio de autenticación
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 2. Request sin autenticación (debería fallar)
curl http://localhost:3003/api/v1/analytics/dashboards

# 3. Request con autenticación
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:3003/api/v1/analytics/dashboards

# 4. Health check (sin autenticación requerida)
curl http://localhost:3003/api/v1/analytics/health
```

### Ejemplo con Python requests

```python
import requests

# Token JWT (obtener del servicio de autenticación)
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Headers con autenticación
headers = {
    "Authorization": f"Bearer {token}"
}

# Request autenticado
response = requests.get(
    "http://localhost:3003/api/v1/analytics/dashboards",
    headers=headers
)

print(response.json())
```

## Seguridad

### Vulnerabilidades Comunes (y cómo las evitamos)

| Vulnerabilidad | Mitigación en este código |
|----------------|---------------------------|
| None algorithm attack | ✅ Especificamos algoritmo explícitamente |
| Weak secret | ✅ Validamos longitud mínima en producción |
| Token sidejacking | ✅ Requiere HTTPS en producción |
| Token replay | ✅ Verificamos expiración (`exp` claim) |
| Injection attacks | ✅ python-jose valida estructura JWT |

## Troubleshooting

### Error: "Missing token"
**Causa**: No se envió el header `Authorization`

**Solución**:
```bash
curl -H "Authorization: Bearer <token>" http://localhost:3003/api/v1/...
```

### Error: "Invalid authorization header format"
**Causa**: Formato incorrecto del header

**Solución**: Debe ser `Bearer <token>`, no solo `<token>`

### Error: "Invalid or expired token"
**Causa**: Token inválido o `JWT_SECRET` no coincide

**Solución**:
1. Verificar que `JWT_SECRET` sea idéntico en ambos servicios
2. Verificar que el token no ha expirado
3. Verificar que el token es un JWT válido en [jwt.io](https://jwt.io)

### Error: "Invalid token payload: missing user ID"
**Causa**: El token no contiene `userId` ni `id`

**Solución**: El servicio que genera tokens debe incluir `userId` o `id` en el payload

## Logging

El middleware registra los siguientes eventos:

### DEBUG Level
```
User authenticated via JWT: 123 (user)
```

### WARN Level
```
Unauthenticated request to /api/v1/analytics/dashboards
JWT validation failed for /api/v1/analytics/dashboards: Signature has expired
```

### ERROR Level
```
Authentication error for /api/v1/analytics/dashboards: <error_message>
```

## Estructura de Archivos

```
app/
├── middleware/
│   ├── __init__.py          # Package exports
│   └── authentication.py    # JWT middleware y helpers
├── core/
│   └── config.py           # JWT_SECRET y ALGORITHM
└── endpoints/
    └── *.py                # Endpoints que usan autenticación

docs/
├── JWT_AUTHENTICATION.md         # Esta documentación
├── JWT_CONFIG_EXPLAINED.md       # Explicación de variables
└── APPLY_AUTH_TO_ENDPOINTS.md   # Guía de uso en endpoints
```

## Referencias

- **Configuración de variables**: [JWT_CONFIG_EXPLAINED.md](JWT_CONFIG_EXPLAINED.md)
- **Aplicar autenticación a endpoints**: [APPLY_AUTH_TO_ENDPOINTS.md](APPLY_AUTH_TO_ENDPOINTS.md)
- **JWT.io**: https://jwt.io/
- **python-jose**: https://python-jose.readthedocs.io/
- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/

## Soporte

Para problemas o preguntas sobre la implementación, consulta:
1. Esta documentación
2. [JWT_CONFIG_EXPLAINED.md](JWT_CONFIG_EXPLAINED.md) - Explicación de variables
3. [APPLY_AUTH_TO_ENDPOINTS.md](APPLY_AUTH_TO_ENDPOINTS.md) - Ejemplos de uso
