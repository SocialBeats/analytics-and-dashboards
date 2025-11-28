# API Gateway Authentication Middleware

## Descripción

Este microservicio implementa un middleware de autenticación que **confía en el API Gateway**.

El API Gateway ya valida los tokens JWT y añade headers con la información del usuario decodificada. Este microservicio simplemente lee esos headers, evitando la validación duplicada del token.

## Patrón de Arquitectura

### API Gateway Pattern - Centralized Authentication

- ✅ El **API Gateway** valida el token JWT una sola vez
- ✅ El Gateway añade headers con información del usuario (`x-user-id`, `x-gateway-authenticated`)
- ✅ Los **microservicios** confían en estos headers y NO validan el token nuevamente

### Ventajas

1. **Rendimiento**: No hay validación duplicada de tokens
2. **Simplicidad**: Microservicios no necesitan conocer `JWT_SECRET`
3. **Seguridad**: Autenticación centralizada en el Gateway
4. **Escalabilidad**: Menos overhead en cada microservicio

## Configuración

### Variables de Entorno

Ya **NO se requiere** configurar `JWT_SECRET` en este microservicio, ya que la validación JWT se hace en el API Gateway.

Si aún tienes `JWT_SECRET` en tu `.env`, puedes eliminarlo de forma segura.

## Rutas Abiertas (Sin Autenticación)

Las siguientes rutas **NO** requieren autenticación:

- `/` - Root endpoint
- `/docs` - Swagger UI
- `/redoc` - ReDoc UI
- `/openapi.json` - OpenAPI schema
- `/api/v1/analytics/health` - Health check

Todas las demás rutas bajo `/api/v1/` **requieren autenticación**.

## Cómo Funciona

### 1. Request con Token JWT al API Gateway

El cliente envía el token JWT al API Gateway en el header `Authorization`:

```http
GET /api/v1/analytics/dashboards
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2. Validación en el API Gateway

El API Gateway:

1. ✅ Valida el token JWT (firma, expiración, etc.)
2. ✅ Decodifica el token y extrae información del usuario
3. ✅ Añade headers con la información del usuario:
   - `x-user-id`: ID del usuario
   - `x-gateway-authenticated`: `"true"`
   - `x-user-email`: Email del usuario (opcional)
   - `x-user-role`: Rol del usuario (opcional)
4. ✅ Reenvía la petición al microservicio con los headers añadidos

### 3. Validación en el Microservicio

El middleware del microservicio:

1. ✅ Verifica que el header `x-gateway-authenticated` existe y es `"true"`
2. ✅ Verifica que el header `x-user-id` existe
3. ✅ Lee los headers adicionales (`x-user-email`, `x-user-role`)
4. ✅ Añade la información al `request.state.user`

### 4. Usuario Autenticado

Si la autenticación es exitosa, `request.state.user` contiene:

```python
{
    "userId": "123",              # ID del usuario (desde x-user-id)
    "email": "user@example.com",  # Email (desde x-user-email)
    "role": "user"                # Rol (desde x-user-role, default: "user")
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

Request no viene del Gateway autenticado:

```json
{
  "detail": "Authentication required. Request must come through API Gateway."
}
```

Falta el user ID del Gateway:

```json
{
  "detail": "Missing user identification from Gateway"
}
```

### 403 Forbidden

Permisos insuficientes:

```json
{
  "detail": "Insufficient permissions. Required roles: admin"
}
```

## Testing

### Testing a través del API Gateway (Producción)

```bash
# 1. Obtener token del servicio de autenticación
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 2. Request a través del API Gateway (puerto 3000)
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:3000/api/v1/analytics/dashboards

# 3. Health check (sin autenticación requerida)
curl http://localhost:3000/api/v1/analytics/health
```

### Testing Directo al Microservicio (Desarrollo)

Para testing directo sin pasar por el Gateway, simula los headers que añade el Gateway:

```bash
# Request con headers del Gateway simulados
curl -H "x-gateway-authenticated: true" \
     -H "x-user-id: 123" \
     -H "x-user-email: test@example.com" \
     -H "x-user-role: user" \
     http://localhost:3003/api/v1/analytics/dashboards

# Health check (sin autenticación requerida)
curl http://localhost:3003/api/v1/analytics/health
```

### Ejemplo con Python requests

#### A través del API Gateway (Producción)

```python
import requests

# Token JWT (obtener del servicio de autenticación)
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Headers con autenticación
headers = {
    "Authorization": f"Bearer {token}"
}

# Request autenticado a través del Gateway
response = requests.get(
    "http://localhost:3000/api/v1/analytics/dashboards",
    headers=headers
)

print(response.json())
```

#### Testing Directo (Desarrollo)

```python
import requests

# Simular headers del Gateway
headers = {
    "x-gateway-authenticated": "true",
    "x-user-id": "123",
    "x-user-email": "test@example.com",
    "x-user-role": "user"
}

# Request directo al microservicio
response = requests.get(
    "http://localhost:3003/api/v1/analytics/dashboards",
    headers=headers
)

print(response.json())
```

## Seguridad

### Consideraciones de Seguridad

**⚠️ IMPORTANTE**: Este microservicio **confía completamente** en el API Gateway para la autenticación.

#### Requisitos de Seguridad

1. **Red Privada**: El microservicio DEBE estar en una red privada, no accesible públicamente
2. **Solo Gateway**: Solo el API Gateway debe poder comunicarse con este microservicio
3. **Firewall**: Configurar firewall para bloquear tráfico directo que no venga del Gateway
4. **HTTPS**: Usar HTTPS entre Gateway y microservicio en producción

#### Vulnerabilidades Mitigadas

| Vulnerabilidad | Cómo se mitiga |
|----------------|----------------|
| Token forgery | El Gateway valida la firma JWT |
| Token expiration | El Gateway verifica expiración |
| Header spoofing | El microservicio solo acepta tráfico del Gateway (red privada) |
| Man-in-the-middle | HTTPS entre Gateway y microservicio |

## Troubleshooting

### Error: "Authentication required. Request must come through API Gateway."

**Causa**: Request no tiene el header `x-gateway-authenticated` o no es `"true"`

**Solución**:

- En producción: Asegúrate de que las peticiones pasen por el API Gateway
- En desarrollo local: Añade el header manualmente para testing:

  ```bash
  curl -H "x-gateway-authenticated: true" -H "x-user-id: 123" http://localhost:3003/api/v1/...
  ```

### Error: "Missing user identification from Gateway"

**Causa**: El header `x-user-id` no está presente

**Solución**:

- Verificar que el API Gateway esté añadiendo correctamente el header `x-user-id`
- Verificar que el token JWT en el Gateway contenga `userId` o `id`

### Error: "Insufficient permissions. Required roles: admin"

**Causa**: El usuario no tiene el rol requerido

**Solución**:

- Verificar el rol del usuario en el token
- Verificar que el Gateway esté pasando correctamente el header `x-user-role`

## Logging

El middleware registra los siguientes eventos:

### DEBUG Level

```text
User authenticated via Gateway: 123 (user)
```

### WARN Level

```text
Unauthenticated request to /api/v1/analytics/dashboards: Missing x-gateway-authenticated header
Authenticated request to /api/v1/analytics/dashboards missing x-user-id header
```

## Estructura de Archivos

```text
app/
├── middleware/
│   ├── __init__.py          # Package exports
│   └── authentication.py    # Gateway authentication middleware
└── endpoints/
    └── *.py                # Endpoints que usan autenticación

docs/
├── jwt_auth/
│   ├── JWT_AUTHENTICATION.md              # Esta documentación
│   ├── AUTHENTICATION_IMPLEMENTATION.md   # Resumen de implementación
│   └── APPLY_AUTH_TO_ENDPOINTS.md         # Guía de uso en endpoints
```

## Referencias

- **Aplicar autenticación a endpoints**: [APPLY_AUTH_TO_ENDPOINTS.md](APPLY_AUTH_TO_ENDPOINTS.md)
- **API Gateway Authentication**: [api-gateway/src/middleware/authentication.js](../../api-gateway/src/middleware/authentication.js)
- **FastAPI Security**: <https://fastapi.tiangolo.com/tutorial/security/>

## Soporte

Para problemas o preguntas sobre la implementación, consulta:

1. Esta documentación
2. [AUTHENTICATION_IMPLEMENTATION.md](AUTHENTICATION_IMPLEMENTATION.md) - Resumen de implementación
3. [APPLY_AUTH_TO_ENDPOINTS.md](APPLY_AUTH_TO_ENDPOINTS.md) - Ejemplos de uso
