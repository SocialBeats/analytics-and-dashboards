"""
Audio analysis module for calculating beat metrics using librosa
"""

import librosa
import numpy as np
from typing import Dict, Tuple, Optional


class AudioAnalyzer:
    """
    Audio analyzer for extracting musical features and metrics from audio files
    using librosa library.
    """

    def __init__(self, audio_path: str):
        """
        Initialize the audio analyzer with an audio file.

        Args:
            audio_path: Path to the audio file
        """
        self.audio_path = audio_path
        self.y, self.sr = librosa.load(audio_path)
        self.duration = librosa.get_duration(y=self.y, sr=self.sr)

    # ==================== CORE METRICS ====================

    def calculate_energy(self) -> float:
        """
        Calculate energy (intensidad sonora general).
        Uses RMS (Root Mean Square) energy.

        Returns:
            Normalized energy value between 0 and 1
        """
        rms = librosa.feature.rms(y=self.y)[0]
        energy = float(np.mean(rms))
        return min(energy * 10, 1.0)

    def calculate_dynamism(self) -> float:
        """
        Calculate dynamism (variación de intensidad en el tiempo).
        Measures the standard deviation of RMS energy over time.

        Returns:
            Normalized dynamism value between 0 and 1
        """
        rms = librosa.feature.rms(y=self.y)[0]
        dynamism = float(np.std(rms))
        return min(dynamism * 20, 1.0)

    def calculate_percussiveness(self) -> float:
        """
        Calculate percussiveness (predominancia de elementos percusivos vs armónicos).
        Uses harmonic-percussive source separation.

        Returns:
            Normalized percussiveness value between 0 and 1
        """
        y_harmonic, y_percussive = librosa.effects.hpss(self.y)
        harmonic_energy = np.sum(y_harmonic ** 2)
        percussive_energy = np.sum(y_percussive ** 2)
        total_energy = harmonic_energy + percussive_energy

        if total_energy == 0:
            return 0.0

        percussiveness = float(percussive_energy / total_energy)
        return percussiveness

    def calculate_brightness(self) -> float:
        """
        Calculate brightness (predominancia de sonidos agudos vs graves).
        Uses spectral centroid as a measure of brightness.

        Returns:
            Normalized brightness value between 0 and 1
        """
        spectral_centroids = librosa.feature.spectral_centroid(y=self.y, sr=self.sr)[0]
        brightness = float(np.mean(spectral_centroids))
        return min(brightness / 4000.0, 1.0)

    def calculate_density(self) -> float:
        """
        Calculate density (cantidad de eventos/ataques por segundo).
        Uses onset detection to count attacks/events.

        Returns:
            Number of events per second
        """
        onset_frames = librosa.onset.onset_detect(y=self.y, sr=self.sr)
        num_onsets = len(onset_frames)
        density = float(num_onsets / self.duration)
        return density

    def calculate_richness(self) -> float:
        """
        Calculate richness (complejidad del contenido armónico).
        Uses spectral complexity measure.

        Returns:
            Normalized richness value between 0 and 1
        """
        spectral_contrast = librosa.feature.spectral_contrast(y=self.y, sr=self.sr)
        richness = float(np.mean(np.std(spectral_contrast, axis=1)))
        return min(richness / 30.0, 1.0)

    def get_core_metrics(self) -> Dict[str, float]:
        """
        Calculate all core metrics.

        Returns:
            Dictionary with all core metrics
        """
        return {
            "energy": self.calculate_energy(),
            "dynamism": self.calculate_dynamism(),
            "percussiveness": self.calculate_percussiveness(),
            "brigthness": self.calculate_brightness(),
            "density": self.calculate_density(),
            "richness": self.calculate_richness()
        }

    # ==================== EXTRA METRICS - TEMPO ====================

    def calculate_tempo_metrics(self) -> Dict[str, Optional[float]]:
        """
        Calculate tempo-related metrics (PRO tier).

        Returns:
            Dictionary with BPM, num_beats, mean_duration, and beats_position
        """
        tempo, beats = librosa.beat.beat_track(y=self.y, sr=self.sr)
        beat_times = librosa.frames_to_time(beats, sr=self.sr)

        num_beats = len(beat_times)
        mean_duration = float(np.mean(np.diff(beat_times))) if num_beats > 1 else 0.0

        beats_position = float(np.mean(beat_times % 4.0)) if num_beats > 0 else 0.0

        return {
            "bpm": float(tempo),
            "num_beats": num_beats,
            "mean_duration": mean_duration,
            "beats_position": beats_position
        }

    # ==================== EXTRA METRICS - TONALITY ====================

    def calculate_tonality_metrics(self) -> Dict[str, Optional[any]]:
        """
        Calculate tonality-related metrics (PRO tier).

        Returns:
            Dictionary with key, uniformity, stability, and chroma_features
        """
        chroma = librosa.feature.chroma_cqt(y=self.y, sr=self.sr)

        key_profile = np.mean(chroma, axis=1)
        key_idx = int(np.argmax(key_profile))
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key = keys[key_idx]

        uniformity = float(1.0 - np.std(key_profile))

        chroma_std = np.std(chroma, axis=1)
        stability = float(1.0 - np.mean(chroma_std))

        chroma_features = {
            f"chroma_{keys[i]}": float(key_profile[i])
            for i in range(12)
        }

        return {
            "key": key,
            "uniformity": uniformity,
            "stability": stability,
            "chroma_features": chroma_features
        }

    # ==================== EXTRA METRICS - SOUND POWER ====================

    def calculate_sound_power(self) -> Dict[str, Optional[float]]:
        """
        Calculate sound power in decibels (PRO tier).

        Returns:
            Dictionary with decibels
        """
        rms = librosa.feature.rms(y=self.y)[0]
        mean_rms = np.mean(rms)

        if mean_rms > 0:
            decibels = float(20 * np.log10(mean_rms))
        else:
            decibels = -np.inf

        return {
            "decibels": decibels if not np.isinf(decibels) else -60.0
        }

    # ==================== EXTRA METRICS - MELODIC PROFILE ====================

    def calculate_melodic_profile(self) -> Dict[str, Optional[float]]:
        """
        Calculate melodic profile metrics (STUDIO tier).

        Returns:
            Dictionary with hz_range and mean_hz
        """
        pitches, magnitudes = librosa.piptrack(y=self.y, sr=self.sr)

        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)

        if len(pitch_values) > 0:
            hz_range = float(np.max(pitch_values) - np.min(pitch_values))
            mean_hz = float(np.mean(pitch_values))
        else:
            hz_range = 0.0
            mean_hz = 0.0

        return {
            "hz_range": hz_range,
            "mean_hz": mean_hz
        }

    # ==================== EXTRA METRICS - TEXTURE ====================

    def calculate_texture_metrics(self) -> Dict[str, Optional[any]]:
        """
        Calculate texture metrics (STUDIO tier).

        Returns:
            Dictionary with character and opening
        """
        spectral_rolloff = librosa.feature.spectral_rolloff(y=self.y, sr=self.sr)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=self.y, sr=self.sr)[0]

        opening = float(np.mean(spectral_bandwidth) / self.sr)

        roughness = np.std(spectral_rolloff)
        if roughness < 500:
            character = "suave"
        elif roughness < 1500:
            character = "moderada"
        else:
            character = "rugosa"

        return {
            "character": character,
            "opening": opening
        }

    # ==================== EXTRA METRICS - ARTICULATION ====================

    def calculate_articulation_metrics(self) -> Dict[str, Optional[any]]:
        """
        Calculate articulation metrics (STUDIO tier).

        Returns:
            Dictionary with style, sudden_changes, soft_changes, and ratio
        """
        onset_env = librosa.onset.onset_strength(y=self.y, sr=self.sr)

        onset_diff = np.diff(onset_env)

        sudden_threshold = np.percentile(np.abs(onset_diff), 75)
        soft_threshold = np.percentile(np.abs(onset_diff), 25)

        sudden_changes = float(np.sum(np.abs(onset_diff) > sudden_threshold))
        soft_changes = float(np.sum(np.abs(onset_diff) <= soft_threshold))

        ratio = sudden_changes / soft_changes if soft_changes > 0 else 0.0

        if ratio > 1.5:
            style = "staccato"
        elif ratio < 0.5:
            style = "legato"
        else:
            style = "moderato"

        return {
            "style": style,
            "suddent_changes": sudden_changes,
            "soft_changes": soft_changes,
            "ratio_sudden_soft": float(ratio)
        }

    # ==================== ALL EXTRA METRICS ====================

    def get_extra_metrics(self) -> Dict[str, Optional[any]]:
        """
        Calculate all extra metrics.

        Returns:
            Dictionary with all extra metrics
        """
        extra_metrics = {}

        extra_metrics.update(self.calculate_tempo_metrics())
        extra_metrics.update(self.calculate_tonality_metrics())
        extra_metrics.update(self.calculate_sound_power())
        extra_metrics.update(self.calculate_melodic_profile())
        extra_metrics.update(self.calculate_texture_metrics())
        extra_metrics.update(self.calculate_articulation_metrics())

        return extra_metrics

    # ==================== MAIN FUNCTION ====================

    def analyze(self) -> Tuple[Dict[str, float], Dict[str, Optional[any]]]:
        """
        Perform complete audio analysis and return all metrics.

        Returns:
            Tuple of (core_metrics, extra_metrics)
        """
        core_metrics = self.get_core_metrics()
        extra_metrics = self.get_extra_metrics()

        return core_metrics, extra_metrics


def analyze_audio_file(audio_path: str) -> Tuple[Dict[str, float], Dict[str, Optional[any]]]:
    """
    Convenience function to analyze an audio file and return all metrics.

    Args:
        audio_path: Path to the audio file

    Returns:
        Tuple of (core_metrics, extra_metrics)
    """
    analyzer = AudioAnalyzer(audio_path)
    return analyzer.analyze()
