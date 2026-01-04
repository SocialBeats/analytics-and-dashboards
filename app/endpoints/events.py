"""
Server-Sent Events endpoint for real-time notifications
"""
import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.core.logging import logger
from app.services.kafka_consumer import kafka_service

router = APIRouter()


@router.get("/metrics-events")
async def metrics_events(request: Request):
    """
    Server-Sent Events endpoint for real-time beat metrics notifications.
    
    This endpoint maintains a persistent connection with the client and sends
    events when beat metrics are completed, eliminating the need for polling.
    
    Events sent:
    - METRICS_COMPLETED: When beat metrics calculation is finished
        Data: { beatId, metricsId, userId }
    
    Usage in frontend:
        const eventSource = new EventSource('/api/v1/analytics/metrics-events');
        eventSource.addEventListener('METRICS_COMPLETED', (e) => {
            const data = JSON.parse(e.data);
            console.log('Metrics completed for beat:', data.beatId);
        });
    """
    
    async def event_generator():
        # Create a queue for this connection
        queue = asyncio.Queue()
        kafka_service.broadcaster.add_connection(queue)
        
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Listening for metrics events'})}\n\n"
            
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.debug("Client disconnected from SSE")
                    break
                
                try:
                    # Wait for events with timeout to allow checking disconnection
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Format as SSE
                    event_type = message.get("type", "message")
                    data = message.get("data", {})
                    
                    # Send event
                    yield f"event: {event_type}\n"
                    yield f"data: {json.dumps(data)}\n\n"
                    
                except asyncio.TimeoutError:
                    # Send keep-alive comment every 30s
                    yield ": keep-alive\n\n"
                    
        except asyncio.CancelledError:
            logger.debug("SSE connection cancelled")
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
        finally:
            kafka_service.broadcaster.remove_connection(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
