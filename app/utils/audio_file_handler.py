"""
Utility functions for handling audio file downloads and temporary storage
"""

import os
import httpx
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from app.core.config import settings


class AudioFileHandler:
    """Handler for audio file operations"""

    def __init__(self):
        self.temp_dir = Path(settings.TEMP_AUDIO_DIR)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def download_from_url(self, url: str, beat_id: str) -> str:
        """
        Download audio file from URL and save to temporary directory.

        Args:
            url: URL of the audio file
            beat_id: Beat ID for naming the file

        Returns:
            Path to the downloaded file

        Raises:
            Exception: If download fails
        """
        file_extension = self._get_extension_from_url(url)
        temp_file_path = self.temp_dir / f"{beat_id}{file_extension}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()

                if len(response.content) > settings.MAX_UPLOAD_SIZE:
                    raise ValueError(
                        f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes"
                    )

                with open(temp_file_path, "wb") as f:
                    f.write(response.content)

                return str(temp_file_path)

            except httpx.HTTPError as e:
                raise Exception(f"Failed to download audio file: {e}")

    async def save_upload(self, file: UploadFile, beat_id: str) -> str:
        """
        Save uploaded audio file to temporary directory.

        Args:
            file: Uploaded file object
            beat_id: Beat ID for naming the file

        Returns:
            Path to the saved file

        Raises:
            Exception: If save fails
        """
        file_extension = self._get_extension_from_filename(file.filename)
        temp_file_path = self.temp_dir / f"{beat_id}{file_extension}"

        try:
            content = await file.read()

            if len(content) > settings.MAX_UPLOAD_SIZE:
                raise ValueError(
                    f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes"
                )

            with open(temp_file_path, "wb") as f:
                f.write(content)

            return str(temp_file_path)

        except Exception as e:
            raise Exception(f"Failed to save uploaded file: {e}")

    def cleanup(self, file_path: str) -> None:
        """
        Remove temporary audio file.

        Args:
            file_path: Path to the file to remove
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

    @staticmethod
    def _get_extension_from_url(url: str) -> str:
        """Extract file extension from URL"""
        path = url.split("?")[0]
        ext = os.path.splitext(path)[1]
        return ext if ext else ".wav"

    @staticmethod
    def _get_extension_from_filename(filename: Optional[str]) -> str:
        """Extract file extension from filename"""
        if not filename:
            return ".wav"
        ext = os.path.splitext(filename)[1]
        return ext if ext else ".wav"
