# Kafka Integration - analytics-and-dashboards

Este documento describe la integración de Apache Kafka en el microservicio `analytics-and-dashboards`, adaptada desde la implementación en Node.js del repositorio `beats-interaction`.

## 📋 Resumen de cambios

### Archivos creados

- **`app/services/kafka_consumer.py`**: Servicio principal de Kafka que maneja la conexión, consumo y producción de mensajes

### Archivos modificados

1. **`app/core/config.py`**: Agregadas variables de configuración para Kafka
2. **`main.py`**: Integración del servicio Kafka en el ciclo de vida de la aplicación
3. **`app/endpoints/health.py`**: Nuevo endpoint de health check para Kafka
4. **`.env.example`**: Agregadas variables de entorno para Kafka
5. **`docker-compose.yml`**: Agregados servicios de Zookeeper y Kafka
6. **`requirements.txt`**: Agregada dependencia `aiokafka==0.11.0`

## 🚀 Características implementadas

### 1. Servicio Kafka (`kafka_consumer.py`)

El servicio incluye las siguientes características principales (alineadas con `kafkaConsumer.js`):

- **Conexión con reintentos infinitos**: Loop infinito que reintenta la conexión con delays configurables
- **Período de cooldown**: Después de agotar los reintentos máximos, entra en cooldown antes de reiniciar
- **Consumer y Producer**: Ambos clientes configurados con `clientId` para identificación
- **Admin Client**: Función `is_kafka_connected()` para verificar conectividad
- **Dead Letter Queue (DLQ)**: Los mensajes que fallan se envían al topic `analytics-dlq`
- **Procesamiento de eventos**: Parseo automático de JSON y manejo de errores
- **Procesamiento asíncrono**: Utiliza asyncio para operaciones no bloqueantes
- **Cálculo automático de métricas**: Escucha el topic `beats-events` y procesa eventos `BEAT_CREATED` para calcular métricas automáticamente

#### Event Handlers Implementados

##### `BEAT_CREATED`

Cuando el microservicio `beats-upload` publica un beat nuevo, se envía un evento por Kafka que este servicio consume automáticamente para calcular las métricas del beat.

**Estructura del evento esperado:**

```json
{
  "type": "BEAT_CREATED",
  "payload": {
    "beatId": "507f1f77bcf86cd799439011",
    "audioUrl": "https://s3.amazonaws.com/bucket/audio.mp3",
    "userId": "507f191e810c19729de860ea"
  }
}
```

**Flujo de procesamiento:**

1. El consumer recibe el evento del topic `beats-events`
2. Extrae `beatId`, `audioUrl` y `userId` del payload
3. Descarga el archivo de audio desde `audioUrl`
4. Analiza el audio con librosa y extrae métricas (BPM, key, energy, etc.)
5. Guarda las métricas en MongoDB en la colección `beat_metrics`
6. Si hay error, envía el evento al DLQ (`analytics-dlq`)

**Diferencias con la versión Node.js:**

- Usa `aiokafka` (Python) en lugar de `kafkajs` (Node.js)
- Implementa el caso de negocio `BEAT_CREATED` específico para este microservicio
- Se puede extender con más handlers en `_process_event()`

### 2. Configuración

Nuevas variables en `app/core/config.py`:

```python
KAFKA_BROKER: str = "localhost:9092"
ENABLE_KAFKA: bool = True
KAFKA_CONNECTION_MAX_RETRIES: int = 10
KAFKA_CONNECTION_RETRY_DELAY: int = 3000  # milliseconds
KAFKA_COOLDOWN: int = 30000  # milliseconds
```

### 3. Endpoints

**GET `/api/v1/kafka/health`**

Verifica el estado de la conexión a Kafka.

Respuesta exitosa (200):

```json
{
  "kafka": "connected",
  "in_cooldown": false,
  "retry_count": 0,
  "enabled": true,
  "timestamp": "2025-12-09T10:30:00.000000"
}
```

Respuesta fallida (503):

```json
{
  "kafka": "disconnected",
  "in_cooldown": false,
  "retry_count": 5,
  "enabled": true,
  "timestamp": "2025-12-09T10:30:00.000000"
}
```

## 🐳 Docker Compose

Se agregaron dos nuevos servicios:

### Zookeeper

```yaml
zookeeper:
  image: confluentinc/cp-zookeeper:7.5.0
  ports:
    - "2181:2181"
```

### Kafka

```yaml
kafka:
  image: confluentinc/cp-kafka:7.5.0
  ports:
    - "9092:9092"
    - "9093:9093"
```

## 📦 Instalación

### Desarrollo local

1. Instalar dependencias:

```bash
pip install -r requirements.txt
```

2. Configurar variables de entorno (copiar desde `.env.example`):

```bash
cp .env.example .env
```

3. Iniciar Kafka y Zookeeper (requiere Docker):

```bash
docker-compose up -d zookeeper kafka
```

4. Iniciar la aplicación:

```bash
python main.py
```

### Con Docker Compose

```bash
docker-compose up --build
```

## 🔧 Configuración de entorno

Variables de entorno necesarias:

```env
# Kafka Configuration
KAFKA_BROKER="localhost:9092"
ENABLE_KAFKA=true
KAFKA_CONNECTION_MAX_RETRIES=10
KAFKA_CONNECTION_RETRY_DELAY=3000
KAFKA_COOLDOWN=30000
```

Para entornos Docker, usar el nombre del servicio:

```env
KAFKA_BROKER="kafka:29092"
```

## 🎯 Uso del servicio Kafka

### Consumir mensajes

El consumer se inicia automáticamente cuando la aplicación arranca y escucha el topic `beats-events` para procesar eventos de beats.

#### Event Handler: BEAT_CREATED

El servicio está configurado para procesar automáticamente eventos `BEAT_CREATED` que envía el microservicio `beats-upload`. Cuando se recibe este evento:

1. Descarga el archivo de audio desde la URL proporcionada
2. Analiza las características del audio (BPM, key, energy, etc.)
3. Calcula las métricas core y extra
4. Guarda los resultados en la base de datos MongoDB

**No se requiere intervención manual** - el proceso es completamente automático.

#### Agregar más handlers

Para procesar eventos personalizados adicionales, agrega más casos en el método `_process_event` en `kafka_consumer.py`:

```python
async def _process_event(self, event: dict):
    """Process individual Kafka events"""
    event_type = event.get("type", "UNKNOWN")
    
    if event_type == "BEAT_CREATED":
        await self._handle_beat_created(event.get("payload"))
    elif event_type == "METRIC_UPDATED":
        # Tu lógica aquí
        await self._handle_metric_updated(event.get("payload"))
    elif event_type == "DASHBOARD_REFRESH":
        # Tu lógica aquí
        await self._handle_dashboard_refresh(event.get("payload"))
    else:
        logger.info(f"Unhandled event type: {event_type}")
```

**Formato esperado de eventos:**

```json
{
  "type": "EVENT_TYPE",
  "payload": {
    // tus datos aquí
  }
}
```

### Subscribirse a topics

El servicio ya está configurado para escuchar el topic `beats-events`. Si necesitas agregar más topics:

```python
# En start_kafka_consumer(), después de await self.consumer.start()
self.consumer.subscribe(["beats-events", "metrics-events", "analytics-events"])
```

### Enviar mensajes

```python
from app.services.kafka_consumer import kafka_service
import json

# Enviar un evento
event = {
    "type": "METRIC_CALCULATED",
    "payload": {"metric": "cpu_usage", "value": 75.5}
}

await kafka_service.send_message(
    topic='analytics-events',
    message=json.dumps(event).encode('utf-8'),
    key=b'metric-123'
)
```

### Dead Letter Queue (DLQ)

Los mensajes que no se pueden procesar correctamente se envían automáticamente al topic `analytics-dlq` con la siguiente estructura:

```json
{
  "originalEvent": "mensaje original que falló",
  "error": "razón del error",
  "timestamp": "2025-12-09T10:30:00.000000"
}
```

### Verificar estado de conexión

```python
# Método 1: Health check rápido
health = await kafka_service.check_health()
print(health)

# Método 2: Verificación completa con admin client
is_connected = await kafka_service.is_kafka_connected()
print(f"Kafka connected: {is_connected}")
```

## 🔄 Lógica de reintentos

La lógica de reintentos replica el comportamiento de `kafkaConsumer.js`:

1. **Intento inicial**: La aplicación intenta conectarse a Kafka al iniciar
2. **Reintentos con delay**: Si falla, reintenta hasta `KAFKA_CONNECTION_MAX_RETRIES` veces con un delay de `KAFKA_CONNECTION_RETRY_DELAY` ms entre intentos
3. **Cooldown**: Después de agotar los reintentos, espera `KAFKA_COOLDOWN` ms antes de volver al paso 1
4. **Loop infinito**: Este proceso continúa indefinidamente hasta lograr una conexión exitosa

Esta estrategia asegura que:

- No se sature el broker con intentos excesivos
- La aplicación pueda recuperarse automáticamente de caídas temporales de Kafka
- Se proporcione tiempo suficiente para que Kafka se reinicie si está down

**Ejemplo de logs durante reconexión:**

```
INFO: Connecting to Kafka... (Attempt 1/10)
ERROR: Kafka connection failed: Connection refused
WARNING: Retrying in 3.0s...
INFO: Connecting to Kafka... (Attempt 2/10)
...
WARNING: Max retries reached. Cooling down for 30.0s before trying again...
```

## 🐛 Troubleshooting

### Kafka no se conecta

1. Verificar que Zookeeper y Kafka estén ejecutándose:

```bash
docker-compose ps
```

2. Revisar logs de Kafka:

```bash
docker-compose logs kafka
```

3. Verificar la configuración del broker en `.env`

### Endpoint de health devuelve "disconnected"

- Verificar la variable `ENABLE_KAFKA` está en `true`
- Comprobar que el broker es accesible desde la aplicación
- Revisar los logs de la aplicación para errores de conexión

## 📚 Referencias

- Commit original de Node.js: [14129db](https://github.com/SocialBeats/beats-interaction/commit/14129db275d8f158a4ed1dc68e6821ec7df990f7)
- Documentación de aiokafka: <https://aiokafka.readthedocs.io/>
- Apache Kafka: <https://kafka.apache.org/documentation/>

## ✅ Checklist de implementación

- [x] Crear servicio Kafka consumer
- [x] Agregar configuración en `config.py`
- [x] Integrar en el lifecycle de FastAPI
- [x] Crear endpoint de health check
- [x] Actualizar docker-compose con Zookeeper y Kafka
- [x] Actualizar `.env.example`
- [x] Agregar dependencia en `requirements.txt`
- [x] Documentación completa
- [x] Implementar handler para evento `BEAT_CREATED`
- [x] Subscribirse al topic `beats-events`
- [x] Integrar con `BeatMetricsService` para cálculo automático

## 🔜 Próximos pasos

1. **Instalar dependencias**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Iniciar servicios Docker**:

   ```bash
   docker-compose up -d zookeeper kafka
   ```

3. **Configurar el microservicio `beats-upload`**:
   - Implementar publicación de eventos `BEAT_CREATED` al topic `beats-events`
   - Incluir `beatId`, `audioUrl` y `userId` en el payload

4. **Testing del flujo completo**:
   - Subir un beat desde `beats-upload`
   - Verificar que el evento se publique a Kafka
   - Confirmar que `analytics-and-dashboards` consume el evento
   - Validar que las métricas se calculen y guarden correctamente

5. **Implementar handlers adicionales** (opcional):
   - Agregar más tipos de eventos según necesidades del negocio
   - Ejemplo: `BEAT_DELETED`, `BEAT_UPDATED`, etc.

6. **Monitoreo y DLQ**:
   - Monitorear el topic `analytics-dlq` para mensajes fallidos
   - Implementar dashboard o alertas para errores

7. **Métricas y observabilidad**:
   - Implementar métricas de mensajes procesados/fallidos
   - Dashboard de salud de Kafka
   - Alertas en caso de desconexión prolongada

8. **Seguridad** (producción):
   - Configurar SASL/SSL para conexión segura
   - Implementar ACLs en Kafka
