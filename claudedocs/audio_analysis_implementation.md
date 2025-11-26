# Audio Analysis Implementation with Librosa

## Overview

Implementation of audio analysis system for calculating beat metrics using the librosa library. The system extracts musical features from audio files and maps them to the BeatMetrics model structure.

## Architecture

### File Structure
- [app/services/audio_analyzer.py](../app/services/audio_analyzer.py) - Main audio analysis module
- [app/models/beat_metrics.py](../app/models/beat_metrics.py) - Data models for metrics
- [scripts/test_audio_analyzer.py](../scripts/test_audio_analyzer.py) - Testing script

## Metrics Implementation

### Core Metrics (Free Tier)

#### 1. **Energy** (Intensidad sonora general)
- **Method**: RMS (Root Mean Square) energy
- **Function**: `librosa.feature.rms()`
- **Output**: Normalized value 0-1
- **Interpretation**: Overall loudness/intensity of the audio

#### 2. **Dynamism** (Variación de intensidad en el tiempo)
- **Method**: Standard deviation of RMS energy over time
- **Function**: `np.std(librosa.feature.rms())`
- **Output**: Normalized value 0-1
- **Interpretation**: How much the intensity varies throughout the track

#### 3. **Percussiveness** (Predominancia de elementos percusivos vs armónicos)
- **Method**: Harmonic-Percussive Source Separation (HPSS)
- **Function**: `librosa.effects.hpss()`
- **Output**: Ratio of percussive energy to total energy (0-1)
- **Interpretation**: Higher values = more percussive, lower = more harmonic

#### 4. **Brightness** (Predominancia de sonidos agudos vs graves)
- **Method**: Spectral centroid
- **Function**: `librosa.feature.spectral_centroid()`
- **Output**: Normalized value 0-1
- **Interpretation**: Higher values = brighter/treble-heavy sound

#### 5. **Density** (Cantidad de eventos/ataques por segundo)
- **Method**: Onset detection
- **Function**: `librosa.onset.onset_detect()`
- **Output**: Number of events per second
- **Interpretation**: How many distinct attacks/events occur per second

#### 6. **Richness** (Complejidad del contenido armónico)
- **Method**: Spectral contrast complexity
- **Function**: `librosa.feature.spectral_contrast()`
- **Output**: Normalized value 0-1
- **Interpretation**: Harmonic complexity and timbral variation

---

### Extra Metrics

#### PRO Tier - Tempo

**1. BPM** (Beats per minute)
- **Function**: `librosa.beat.beat_track()`
- **Output**: Float (e.g., 120.5)

**2. num_beats** (Total beats detected)
- **Function**: Count of detected beat frames
- **Output**: Integer

**3. mean_duration** (Average duration between beats)
- **Function**: Mean of time differences between consecutive beats
- **Output**: Float (seconds)

**4. beats_position** (Beat positions in rhythmic structure)
- **Function**: Mean of beat times modulo 4
- **Output**: Float (0-4 range)

#### PRO Tier - Tonality

**1. key** (Musical key)
- **Function**: `librosa.feature.chroma_cqt()` + peak detection
- **Output**: String (e.g., "C", "D#", "Am")
- **Method**: Analyzes chroma features to determine dominant pitch class

**2. uniformity** (Tonal uniformity)
- **Function**: 1 - std(chroma profile)
- **Output**: Float (0-1)
- **Interpretation**: How consistent the tonal profile is

**3. stability** (Tonal stability over time)
- **Function**: 1 - mean(std of chroma over time)
- **Output**: Float (0-1)
- **Interpretation**: How stable the key/tonality remains

**4. chroma_features** (Detailed chromatic features)
- **Output**: Dictionary with all 12 pitch classes
- **Format**: `{"chroma_C": 0.5, "chroma_C#": 0.3, ...}`

#### PRO Tier - Sound Power

**1. decibels** (Sound power in dB)
- **Function**: `20 * log10(RMS)`
- **Output**: Float (dB scale)
- **Interpretation**: Loudness in decibels

#### PREMIUM Tier - Melodic Profile

**1. hz_range** (Frequency range in Hz)
- **Function**: `librosa.piptrack()` - max pitch - min pitch
- **Output**: Float (Hz)
- **Interpretation**: Melodic range span

**2. mean_hz** (Average melodic frequency)
- **Function**: Mean of detected pitches
- **Output**: Float (Hz)
- **Interpretation**: Average pitch of melodic content

#### PREMIUM Tier - Texture

**1. character** (Texture character)
- **Function**: Classification based on spectral rolloff variance
- **Output**: String ("suave", "moderada", "rugosa")
- **Interpretation**: Smoothness vs roughness of the sound texture

**2. opening** (Texture opening/spread)
- **Function**: `librosa.feature.spectral_bandwidth()`
- **Output**: Float (normalized)
- **Interpretation**: How spread out the frequency content is

#### PREMIUM Tier - Articulation

**1. style** (Articulation style)
- **Function**: Classification based on onset change ratio
- **Output**: String ("legato", "moderato", "staccato")
- **Interpretation**: How connected vs separated the notes are

**2. suddent_changes** (Sudden articulation changes)
- **Function**: Count of onset strength changes above 75th percentile
- **Output**: Float (count)

**3. soft_changes** (Soft articulation changes)
- **Function**: Count of onset strength changes below 25th percentile
- **Output**: Float (count)

**4. ratio_sudden_soft** (Ratio of sudden to soft changes)
- **Function**: sudden_changes / soft_changes
- **Output**: Float
- **Interpretation**: Balance between abrupt and gradual changes

## Usage

### Basic Usage

```python
from app.services.audio_analyzer import analyze_audio_file

core_metrics, extra_metrics = analyze_audio_file("path/to/audio.wav")
```

### Using the AudioAnalyzer Class

```python
from app.services.audio_analyzer import AudioAnalyzer

analyzer = AudioAnalyzer("path/to/audio.wav")

core_metrics = analyzer.get_core_metrics()

extra_metrics = analyzer.get_extra_metrics()

tempo_metrics = analyzer.calculate_tempo_metrics()
tonality_metrics = analyzer.calculate_tonality_metrics()
```

### Testing

```bash
python scripts/test_audio_analyzer.py path/to/audio.wav
```

## Dependencies

Required Python packages (added to requirements.txt):
- `librosa==0.10.1` - Audio analysis library
- `numpy==1.26.2` - Numerical computing
- `soundfile==0.12.1` - Audio file I/O

Install with:
```bash
pip install -r requirements.txt
```

## Supported Audio Formats

Librosa supports various audio formats through soundfile and audioread:
- WAV
- MP3
- FLAC
- OGG
- M4A
- And more...

## Integration with BeatMetrics Service

To integrate with the BeatMetrics service:

```python
from app.services.audio_analyzer import analyze_audio_file
from app.schemas.beat_metrics import BeatMetricsCreate
from app.models.beat_metrics import CoreMetrics, ExtraMetrics

core_metrics_dict, extra_metrics_dict = analyze_audio_file(audio_path)

beat_metrics = BeatMetricsCreate(
    beatId="beat_12345",
    coreMetrics=CoreMetrics(**core_metrics_dict),
    extraMetrics=ExtraMetrics(**extra_metrics_dict)
)
```

## Performance Considerations

- **Processing Time**: Varies based on audio length and sample rate
  - Typical 3-minute track: 5-15 seconds
- **Memory Usage**: Proportional to audio length
  - Librosa loads entire audio into memory
- **Optimization Tips**:
  - Use lower sample rates for faster processing if high precision not needed
  - Process audio files asynchronously for API endpoints
  - Consider caching results for frequently accessed tracks

## Future Enhancements

Potential improvements:
1. **Batch Processing**: Analyze multiple files concurrently
2. **Streaming Analysis**: Process long files in chunks
3. **ML-based Features**: Genre classification, mood detection
4. **Visualization**: Generate spectrograms, waveforms
5. **Advanced Tempo**: Multi-tempo detection, tempo changes
6. **Segment Analysis**: Analyze intro/verse/chorus sections separately

## References

- [Librosa Documentation](https://librosa.org/doc/latest/index.html)
- [MIR (Music Information Retrieval) Techniques](https://www.audiolabs-erlangen.de/resources/MIR)
- [Audio Feature Extraction Overview](https://musicinformationretrieval.com/)
