# Guía de Setup con Docker

## Inicio Rápido

```bash
# 1. Iniciar todos los servicios (API + MongoDB + Redis)
docker-compose up -d

# 2. Verificar que todos los servicios están corriendo
docker-compose ps

# 3. Ver logs
docker-compose logs -f api
```

## Servicios Incluidos

### 1. API (FastAPI Application)
- **Container**: `analytics-service`
- **Puerto**: 3003
- **URL**: http://localhost:3003

### 2. MongoDB
- **Container**: `mongodb`
- **Puerto**: 27017
- **Database**: `fastapi_template`

### 3. Redis (Rate Limiting)
- **Container**: `analytics-redis`
- **Puerto**: 6379
- **Uso**: Rate limiting distribuido

### 4. Mongo Express (Opcional)
- **Container**: `mongo_express`
- **Puerto**: 8081
- **Activar**: `docker-compose --profile dev up -d`

## Verificar Rate Limiter con Redis

### Paso 1: Verificar Conexión a Redis

```bash
# Ping a Redis
docker exec -it analytics-redis redis-cli ping
# Respuesta: PONG

# Ver información de Redis
docker exec -it analytics-redis redis-cli INFO server
```

### Paso 2: Monitorear Logs del API

```bash
docker-compose logs -f api

# Deberías ver:
# ✅ Redis connected for rate limiting
```

### Paso 3: Probar Rate Limiting

```bash
# Hacer peticiones de prueba
for i in {1..12}; do
  curl -H "Authorization: Bearer YOUR_TOKEN" \
       http://localhost:3003/api/v1/rate-limit-examples/dynamic
  echo "Request $i"
  sleep 1
done
```

### Paso 4: Ver Rate Limit Keys en Redis

```bash
# Conectar a Redis CLI
docker exec -it analytics-redis redis-cli

# Listar todas las keys de rate limiting
KEYS rate_limit:*

# Ver valor de una key específica
GET rate_limit:user:12345

# Salir
exit
```

## Variables de Entorno en Docker

El `docker-compose.yml` configura automáticamente:

```yaml
environment:
  - MONGODB_URL=redis://mongodb:27017
  - REDIS_URL=redis://redis:6379     # ← Conexión a Redis
  - ENVIRONMENT=development
  - DEBUG=true
```

**IMPORTANTE**:
- Dentro de Docker, usa nombres de servicios: `redis://redis:6379`
- NO uses `localhost` dentro del contenedor
- `redis` es el nombre del servicio en docker-compose

## Comandos Útiles

### Reiniciar servicios

```bash
# Reiniciar solo el API
docker-compose restart api

# Reiniciar Redis
docker-compose restart redis

# Reiniciar todo
docker-compose restart
```

### Ver logs

```bash
# Logs del API
docker-compose logs -f api

# Logs de Redis
docker-compose logs -f redis

# Logs de todos los servicios
docker-compose logs -f
```

### Limpiar y reconstruir

```bash
# Parar y eliminar contenedores
docker-compose down

# Eliminar también volúmenes (CUIDADO: borra datos)
docker-compose down -v

# Reconstruir imágenes
docker-compose build --no-cache

# Iniciar de nuevo
docker-compose up -d
```

### Inspeccionar Redis

```bash
# Entrar al contenedor de Redis
docker exec -it analytics-redis sh

# Ver configuración de Redis
redis-cli CONFIG GET *

# Monitorear comandos en tiempo real
redis-cli MONITOR

# Ver estadísticas
redis-cli INFO stats
```

## Troubleshooting

### Redis no se conecta

```bash
# Verificar que Redis está corriendo
docker-compose ps redis

# Ver logs de Redis
docker-compose logs redis

# Verificar health check
docker inspect analytics-redis | grep -A 10 Health
```

### API no encuentra Redis

Verificar la variable de entorno en el contenedor:

```bash
docker exec -it analytics-service env | grep REDIS
# Debe mostrar: REDIS_URL=redis://redis:6379
```

### Rate Limiting no funciona

1. **Verificar logs del API**:
```bash
docker-compose logs api | grep -i redis
```

2. **Debería mostrar**:
```
✅ Redis connected for rate limiting
```

3. **Si muestra**:
```
⚠️ Redis not available, using in-memory rate limiting
```

Entonces hay un problema de conexión. Verifica que Redis esté healthy.

## Desarrollo Local vs Docker

### Local (sin Docker)

```bash
# .env
REDIS_URL="redis://localhost:6379"

# Iniciar Redis local
docker run -d -p 6379:6379 redis:7-alpine

# Iniciar API
python main.py
```

### Docker (recomendado)

```bash
# docker-compose.yml ya configurado
REDIS_URL="redis://redis:6379"

# Iniciar todo
docker-compose up -d
```

## Health Checks

Todos los servicios tienen health checks:

```bash
# Ver estado de salud
docker-compose ps

# Debería mostrar:
# NAME                  STATUS
# analytics-service     Up (healthy)
# analytics-redis       Up (healthy)
# mongodb              Up (healthy)
```

## Persistencia de Datos

Los datos se guardan en volúmenes de Docker:

```bash
# Listar volúmenes
docker volume ls | grep analytics

# Resultados:
# analytics-and-dashboards_mongodb_data
# analytics-and-dashboards_redis_data
```

### Backup de Redis

```bash
# Crear backup
docker exec analytics-redis redis-cli SAVE

# Copiar archivo de backup
docker cp analytics-redis:/data/dump.rdb ./redis-backup.rdb
```

### Restaurar Redis

```bash
# Copiar backup al contenedor
docker cp ./redis-backup.rdb analytics-redis:/data/dump.rdb

# Reiniciar Redis
docker-compose restart redis
```

## URLs de Acceso

Con Docker Compose corriendo:

- **API**: http://localhost:3003
- **API Docs**: http://localhost:3003/docs
- **MongoDB**: mongodb://localhost:27017
- **Redis**: redis://localhost:6379
- **Mongo Express** (con `--profile dev`): http://localhost:8081

## Próximos Pasos

1. ✅ Servicios corriendo con `docker-compose up -d`
2. ✅ Verificar logs: `docker-compose logs -f`
3. ✅ Probar API: http://localhost:3003/docs
4. ✅ Probar rate limiting: http://localhost:3003/api/v1/rate-limit-examples/info
5. ✅ Monitorear Redis: `docker exec -it analytics-redis redis-cli MONITOR`

## Referencias

- [docker-compose.yml](../docker-compose.yml)
- [Rate Limiter Usage](./rate_limiter_usage.md)
- [Rate Limit Window Reset](./rate_limiter_window_reset.md)
