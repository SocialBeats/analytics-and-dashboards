# Rate Limiter - Guía Completa

## 🚀 Inicio Rápido

```bash
# 1. Iniciar servicios (API + MongoDB + Redis)
docker-compose up -d

# 2. Verificar Redis conectado
docker-compose logs api | grep -i redis
# Debe mostrar: ✅ Redis connected for rate limiting

# 3. Probar rate limiting
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:3003/api/v1/rate-limit-examples/info
```

---

## 📊 Límites por Plan

| Plan | Requests/Minuto |
|------|-----------------|
| Free | 20 |
| Pro | 50 |
| Studio | 200 |
| No autenticado | 10 |

---

## 💻 Uso en Código

> **⚠️ IMPORTANTE**: Todos los endpoints con rate limiting deben incluir `Response` en los parámetros para que SlowAPI pueda inyectar los headers de rate limiting.

### Límite Dinámico (Recomendado)
Ajusta automáticamente según el plan del usuario:

```python
from fastapi import APIRouter, Request, Response
from app.middleware.rate_limiter import limiter, get_dynamic_rate_limit

router = APIRouter()

@router.get("/dashboards")
@limiter.limit(get_dynamic_rate_limit())
async def list_dashboards(request: Request, response: Response):
    return {"data": "..."}
```

### Límite Fijo
Para endpoints públicos o sin autenticación:

```python
@router.get("/public-endpoint")
@limiter.limit("30/minute")
async def public_endpoint(request: Request):
    return {"data": "..."}
```

### Límite Estricto
Para operaciones costosas (exports, reports):

```python
from app.middleware.rate_limiter import limiter, STRICT_RATE_LIMIT

@router.get("/export-data")
@limiter.limit(STRICT_RATE_LIMIT)  # 5 requests cada 15 minutos
async def export_data(request: Request):
    return {"data": "..."}
```

### Sin Límite
Solo para health checks o webhooks:

```python
@router.get("/health")
@limiter.exempt
async def health_check(request: Request):
    return {"status": "ok"}
```

---

## 🔄 Cómo Funciona el Reset de Peticiones

### Sistema de Ventana Deslizante

El rate limiter usa **sliding window** (ventana deslizante), no ventana fija:

```text
❌ Ventana Fija (NO usamos esto):
Minuto 1: |----10 req----|
Minuto 2:                 |----10 req----|
          0s            60s             120s
Problema: Permite burst de 20 req entre minutos

✅ Ventana Deslizante (LO QUE USAMOS):
Cada request mira hacia atrás 60 segundos:
t=0s:   [últimos 60s]  = 1 req
t=30s:  [últimos 60s]  = 2 req
t=60s:  [últimos 60s]  = 1 req (la de t=0s ya no cuenta)
```

### Ejemplo Práctico: Plan Free (10 req/min)

**Escenario: Usuario hace 10 peticiones en 5 segundos**

```text
t=0s:    Requests 1-10   ✅ (todas pasan, 10/10)
t=5s:    Request 11      ❌ BLOQUEADO (10/10 en ventana)
t=30s:   Request 12      ❌ BLOQUEADO (10/10 en ventana)
t=45s:   Request 13      ❌ BLOQUEADO (10/10 en ventana)
t=60s:   Request 14      ✅ PERMITIDO (las 10 primeras expiraron)

El reset completo ocurre 60 segundos después de la PRIMERA petición.
```

**Escenario: Recuperación Gradual**

```text
t=0s:    Request 1       ✅ (1/10)
t=10s:   Request 2       ✅ (2/10)
...
t=50s:   Request 10      ✅ (10/10)
t=55s:   Request 11      ❌ BLOQUEADO (10/10)
t=60s:   Request 12      ✅ (9/10 - la de t=0s expiró)
t=70s:   Request 13      ✅ (9/10 - la de t=10s expiró)

Los slots se liberan GRADUALMENTE según expiran las peticiones antiguas.
```

### Headers de Respuesta

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 10              # Límite total
X-RateLimit-Remaining: 7           # Peticiones disponibles
X-RateLimit-Reset: 1732713600      # Unix timestamp del reset
```

### Respuesta al Exceder Límite

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1732713600
Retry-After: 45

{
  "error": "Too many requests",
  "message": "Rate limit exceeded for free plan",
  "currentPlan": "free",
  "upgradeInfo": "Upgrade your plan for higher limits",
  "retryAfter": "45 seconds"
}
```

---

## 🐳 Docker Setup

### Configuración en docker-compose.yml

Ya está configurado automáticamente:

```yaml
services:
  api:
    environment:
      - REDIS_URL=redis://redis:6379  # ← Conexión a Redis
    depends_on:
      redis:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    container_name: analytics-redis
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
```

### Comandos Útiles

```bash
# Verificar Redis
docker exec -it analytics-redis redis-cli ping
# Respuesta esperada: PONG

# Ver logs del API
docker-compose logs -f api

# Ver rate limit keys en Redis
docker exec -it analytics-redis redis-cli KEYS "rate_limit:*"

# Monitorear rate limiting en tiempo real
docker exec -it analytics-redis redis-cli MONITOR

# Reiniciar servicios
docker-compose restart api redis
```

---

## 🧪 Testing

### Test Básico

```bash
# Hacer 25 peticiones (plan free = 20/min)
for i in {1..25}; do
  curl -H "Authorization: Bearer YOUR_TOKEN" \
       http://localhost:3003/api/v1/rate-limit-examples/dynamic
  echo "Request $i"
done

# Las últimas 5 deberían retornar 429 Too Many Requests
```

### Endpoints de Ejemplo

- `/api/v1/rate-limit-examples/basic` - Límite fijo
- `/api/v1/rate-limit-examples/dynamic` - Límite por plan
- `/api/v1/rate-limit-examples/strict` - Límite estricto
- `/api/v1/rate-limit-examples/info` - Info de límites

---

## 🔍 Monitoreo

### Logs Importantes

```bash
docker-compose logs api | grep -i "rate limit"

# Mensajes clave:
✅ Redis connected for rate limiting          # Redis OK
⚠️ Redis not available, using in-memory      # Fallback mode
Rate limit exceeded for user: xyz (plan: basic)  # Usuario bloqueado
```

---

## ⚙️ Configuración Avanzada

### Múltiples Límites en un Endpoint

```python
@router.post("/intensive")
@limiter.limit("10/minute")   # Límite de burst
@limiter.limit("100/hour")    # Límite sostenido
async def intensive_operation(request: Request):
    return {"status": "ok"}
```

### Diferentes Ventanas de Tiempo

```python
@limiter.limit("10/second")   # 10 peticiones por segundo
@limiter.limit("60/minute")   # 60 peticiones por minuto
@limiter.limit("1000/hour")   # 1000 peticiones por hora
@limiter.limit("10000/day")   # 10000 peticiones por día
```

### Cambiar Límites por Plan

Edita [app/middleware/rate_limiter.py](../app/middleware/rate_limiter.py):

```python
def get_rate_limit_for_user(request: Request) -> str:
    # Límites por plan
    limits = {
        "free": "10/minute",      # ← Modifica aquí
        "pro": "50/minute",
        "studio": "200/minute",
        "enterprise": "1000/minute",
    }
```

---

## 🆘 Troubleshooting

### Redis no se conecta

```bash
# 1. Verificar que Redis está corriendo
docker-compose ps redis

# 2. Ver logs de Redis
docker-compose logs redis

# 3. Verificar health
docker inspect analytics-redis | grep -A 5 Health

# 4. Ping manual
docker exec -it analytics-redis redis-cli ping
```

### Rate Limiting no funciona

1. **Verificar decorador aplicado**:
```python
# ✅ Correcto
@router.get("/endpoint")
@limiter.limit(get_dynamic_rate_limit())

# ❌ Incorrecto
@router.get("/endpoint")
# Falta el decorador
```

2. **Verificar logs**:
```bash
docker-compose logs api | grep -i redis
# Debe mostrar: ✅ Redis connected
```

3. **Verificar autenticación**:
El rate limiting depende de `request.state.user` del middleware de autenticación.

### Fallback a In-Memory

Si ves este warning:
```
⚠️ Redis not available, using in-memory rate limiting
```

El sistema sigue funcionando pero:
- Los contadores no se comparten entre instancias
- Los contadores se pierden al reiniciar
- Cada instancia aplica su propio límite

**Solución**: Asegúrate que Redis está corriendo con `docker-compose up -d redis`

---

## ❓ FAQ

**¿Cuándo se resetea el contador?**
60 segundos después de la primera petición en la ventana. Es gradual, no de golpe.

**¿Funciona sin Redis?**
Sí, automáticamente usa memoria local como fallback.

**¿Se pierde el contador al reiniciar?**
Con Redis: No. Sin Redis: Sí.

**¿Puedo tener diferentes límites por endpoint?**
Sí, usa decoradores específicos con diferentes valores.

**¿Cómo identifica a los usuarios?**
1. Si está autenticado: usa `userId` del JWT
2. Si no: usa dirección IP

**¿El límite es global o por endpoint?**
Es por usuario/IP en cada endpoint que tenga el decorador.

---

## 📁 Archivos Importantes

### Código
- [app/middleware/rate_limiter.py](../app/middleware/rate_limiter.py) - Implementación
- [app/endpoints/rate_limit_example.py](../app/endpoints/rate_limit_example.py) - Ejemplos

### Configuración
- [app/core/config.py](../app/core/config.py) - Settings con REDIS_URL
- [main.py](../main.py) - Integración del rate limiter
- [docker-compose.yml](../docker-compose.yml) - Servicio Redis
- [.env.example](../.env.example) - Variables de entorno

---

**Implementado**: 2025-11-27
**Tecnologías**: FastAPI + SlowAPI + Redis
