# Beat Metrics Integration Guide

## Overview

This guide explains how to use the automatic audio analysis feature when creating BeatMetrics records. The system automatically calculates all metrics from audio files.

## Architecture

### Complete Flow

```
Audio File → Upload/URL → Analysis → Metrics Calculation → Database Storage
```

### Components

1. **[app/endpoints/beat_metrics.py](../app/endpoints/beat_metrics.py)** - API endpoint for creating beat metrics
2. **[app/services/beat_metrics_service.py](../app/services/beat_metrics_service.py)** - Business logic and orchestration
3. **[app/services/audio_analyzer.py](../app/services/audio_analyzer.py)** - Audio analysis using librosa
4. **[app/utils/audio_file_handler.py](../app/utils/audio_file_handler.py)** - File handling utilities
5. **[app/schemas/beat_metrics.py](../app/schemas/beat_metrics.py)** - Request/response schemas
6. **[app/models/beat_metrics.py](../app/models/beat_metrics.py)** - Database models

## API Usage

### Endpoint

```
POST /analytics/beat-metrics
```

### Option 1: Upload Audio File

```bash
curl -X POST "http://localhost:3003/analytics/beat-metrics" \
  -F "beatId=beat_12345" \
  -F "audioFile=@/path/to/audio.wav"
```

### Option 2: Provide Audio URL

```bash
curl -X POST "http://localhost:3003/analytics/beat-metrics" \
  -F "beatId=beat_12345" \
  -F "audioUrl=https://example.com/audio/beat.mp3"
```

### Python Example with Requests

```python
import requests

# Option 1: Upload file
with open('audio.wav', 'rb') as f:
    response = requests.post(
        'http://localhost:3003/analytics/beat-metrics',
        data={'beatId': 'beat_12345'},
        files={'audioFile': f}
    )

# Option 2: Use URL
response = requests.post(
    'http://localhost:3003/analytics/beat-metrics',
    data={
        'beatId': 'beat_12345',
        'audioUrl': 'https://example.com/audio/beat.mp3'
    }
)

print(response.json())
```

### JavaScript/TypeScript Example

```typescript
// Option 1: Upload file
const formData = new FormData();
formData.append('beatId', 'beat_12345');
formData.append('audioFile', audioFileBlob, 'beat.wav');

const response = await fetch('http://localhost:3003/analytics/beat-metrics', {
  method: 'POST',
  body: formData
});

// Option 2: Use URL
const formData = new FormData();
formData.append('beatId', 'beat_12345');
formData.append('audioUrl', 'https://example.com/audio/beat.mp3');

const response = await fetch('http://localhost:3003/analytics/beat-metrics', {
  method: 'POST',
  body: formData
});

const data = await response.json();
```

## Response Format

```json
{
  "beatId": "beat_12345",
  "coreMetrics": {
    "energy": 0.83,
    "dynamism": 0.61,
    "percussiveness": 0.74,
    "brigthness": 0.56,
    "density": 7.2,
    "richness": 0.68
  },
  "extraMetrics": {
    "bpm": 122.5,
    "num_beats": 245,
    "mean_duration": 0.489,
    "beats_position": 2.1,
    "key": "Am",
    "uniformity": 0.85,
    "stability": 0.78,
    "chroma_features": {
      "chroma_C": 0.45,
      "chroma_C#": 0.23,
      "chroma_D": 0.67,
      ...
    },
    "decibels": -12.5,
    "hz_range": 4500.0,
    "mean_hz": 440.0,
    "character": "moderada",
    "opening": 0.42,
    "style": "staccato",
    "suddent_changes": 145.0,
    "soft_changes": 89.0,
    "ratio_sudden_soft": 1.63
  },
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": null
}
```

## Error Handling

### Error Types

1. **400 Bad Request** - Missing both audioFile and audioUrl
   ```json
   {
     "detail": "Either audio file upload or audioUrl must be provided"
   }
   ```

2. **422 Unprocessable Entity** - Audio processing failed
   ```json
   {
     "detail": "Failed to analyze audio file: Invalid audio format"
   }
   ```

3. **422 Unprocessable Entity** - Invalid metrics data
   ```json
   {
     "detail": "Invalid metrics data from audio analysis: Missing required field"
   }
   ```

4. **500 Internal Server Error** - Database or unexpected error
   ```json
   {
     "detail": "Unexpected error creating beat metrics: ..."
   }
   ```

## Configuration

### Environment Variables

Add to `.env` file:

```env
# File Storage Configuration
TEMP_AUDIO_DIR=temp_audio
MAX_UPLOAD_SIZE=104857600  # 100MB in bytes
```

### Settings

Configuration is managed in [app/core/config.py](../app/core/config.py):

- `TEMP_AUDIO_DIR`: Directory for temporary audio files (default: "temp_audio")
- `MAX_UPLOAD_SIZE`: Maximum file size in bytes (default: 100MB)

## Supported Audio Formats

The system supports all formats that librosa can read:
- WAV
- MP3
- FLAC
- OGG
- M4A
- AAC
- WMA

## Processing Flow

### 1. File Handling
```python
# Upload: audioFile → save to temp_audio/
# URL: audioUrl → download to temp_audio/
```

### 2. Audio Analysis
```python
# Load audio with librosa
# Calculate core metrics (6 metrics)
# Calculate extra metrics (18 metrics)
```

### 3. Database Storage
```python
# Create BeatMetrics document
# Store in MongoDB
# Return serialized response
```

### 4. Cleanup
```python
# Remove temporary audio file
# (Happens automatically even if errors occur)
```

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Verify Installation

```bash
python -c "import librosa; print(librosa.__version__)"
```

### 3. Create Temp Directory

The directory is created automatically, but you can create it manually:

```bash
mkdir -p temp_audio
```

## Testing

### Manual Test with Sample Audio

```bash
# 1. Start the server
uvicorn app.main:app --reload --port 3003

# 2. Test with a sample audio file
curl -X POST "http://localhost:3003/analytics/beat-metrics" \
  -F "beatId=test_beat_001" \
  -F "audioFile=@sample.wav" \
  -v
```

### Using the Test Script

```bash
python scripts/test_audio_analyzer.py path/to/audio.wav
```

This will output all calculated metrics to the console.

## Performance Considerations

### Processing Time
- **Short tracks (< 2 min)**: 3-8 seconds
- **Medium tracks (2-5 min)**: 8-20 seconds
- **Long tracks (> 5 min)**: 20-40 seconds

### Optimization Tips

1. **Async Processing**: The endpoint is already async, but consider background tasks for production
2. **Rate Limiting**: Implement rate limiting to prevent abuse
3. **Caching**: Cache results for frequently analyzed beats
4. **Queue System**: Use Celery or similar for large-scale processing

### Example: Background Task (Future Enhancement)

```python
from fastapi import BackgroundTasks

@router.post("/analytics/beat-metrics")
async def create_beat_metrics(
    background_tasks: BackgroundTasks,
    beatId: str = Form(...),
    audioFile: Optional[UploadFile] = File(None),
    service: BeatMetricsService = Depends(get_beat_metrics_service)
):
    # Add analysis to background tasks
    background_tasks.add_task(
        service.create_async,
        beatId,
        audioFile
    )
    return {"status": "processing", "beatId": beatId}
```

## Security Considerations

### File Validation
- Maximum file size enforced (100MB default)
- File type validation through librosa (fails on invalid audio)
- Temporary files automatically cleaned up

### Best Practices
1. Validate beatId format before processing
2. Implement authentication/authorization
3. Add rate limiting per user/IP
4. Scan uploaded files for malware
5. Use HTTPS in production

## Integration with External Systems

### Example: Integration with Beat Upload Service

```python
# In your beat upload service
async def upload_beat(beat_file, beat_metadata):
    # 1. Store beat file in your storage (S3, etc.)
    beat_url = await storage.upload(beat_file)

    # 2. Create beat record in your database
    beat_id = await beats_db.create({
        "url": beat_url,
        "metadata": beat_metadata
    })

    # 3. Trigger metrics calculation
    analytics_response = await httpx.post(
        "http://analytics-service:3003/analytics/beat-metrics",
        data={"beatId": beat_id, "audioUrl": beat_url}
    )

    return {
        "beat_id": beat_id,
        "metrics": analytics_response.json()
    }
```

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'librosa'`
```bash
# Solution
pip install librosa soundfile numpy
```

**Issue**: `FileNotFoundError: temp_audio directory not found`
```bash
# Solution
mkdir -p temp_audio
```

**Issue**: `Audio processing failed: Could not read audio file`
```bash
# Solution: Ensure ffmpeg is installed for MP3 support
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

**Issue**: `File too large`
```bash
# Solution: Increase MAX_UPLOAD_SIZE in .env
MAX_UPLOAD_SIZE=209715200  # 200MB
```

## Monitoring

### Recommended Metrics to Track

1. **Processing Time**: Track analysis duration per file
2. **Success Rate**: Monitor failed vs successful analyses
3. **Error Types**: Categorize errors for debugging
4. **File Sizes**: Track average file sizes being processed
5. **Queue Length**: If using background tasks

### Example Logging

```python
import logging

logger = logging.getLogger(__name__)

# In beat_metrics_service.py
async def create(...):
    start_time = time.time()
    try:
        # ... processing ...
        duration = time.time() - start_time
        logger.info(f"Successfully analyzed beat {beatId} in {duration:.2f}s")
    except Exception as e:
        logger.error(f"Failed to analyze beat {beatId}: {e}")
```

## Future Enhancements

Potential improvements:
1. **Batch Processing**: Analyze multiple beats in parallel
2. **Webhook Support**: Notify external services when analysis completes
3. **Partial Metrics**: Allow requesting only specific metric tiers (core, pro, studio)
4. **Caching**: Cache analysis results to avoid reprocessing
5. **ML Features**: Genre classification, mood detection
6. **Comparison API**: Compare metrics between different beats
