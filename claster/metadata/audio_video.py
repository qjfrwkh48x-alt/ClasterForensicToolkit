"""
Audio (MP3, FLAC, etc.) and video (MP4, AVI, etc.) metadata extraction using mutagen and hachoir.
"""

from pathlib import Path
from typing import Dict, Any

from claster.core.logger import get_logger

logger = get_logger(__name__)


def get_audio_metadata(audio_path: str) -> Dict[str, Any]:
    """
    Extract metadata from audio file (MP3, FLAC, OGG, M4A, etc.).

    Returns:
        Dictionary with title, artist, album, duration, bitrate, etc.
    """
    try:
        from mutagen import File
    except ImportError:
        logger.error("mutagen is required for audio metadata.")
        return {}

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        audio = File(path)
        if audio is None:
            return {}

        metadata = {
            'duration': audio.info.length if hasattr(audio.info, 'length') else None,
            'bitrate': audio.info.bitrate if hasattr(audio.info, 'bitrate') else None,
            'sample_rate': audio.info.sample_rate if hasattr(audio.info, 'sample_rate') else None,
            'channels': audio.info.channels if hasattr(audio.info, 'channels') else None,
        }

        # Extract tags (ID3 for MP3, Vorbis for FLAC/OGG, etc.)
        tags = {}
        if hasattr(audio, 'tags') and audio.tags:
            for key, value in audio.tags.items():
                if isinstance(value, list):
                    tags[key] = [str(v) for v in value]
                else:
                    tags[key] = str(value)
        metadata['tags'] = tags

        # Common fields
        for field in ['title', 'artist', 'album', 'genre', 'date', 'tracknumber']:
            if field in tags:
                metadata[field] = tags[field]

        return metadata
    except Exception as e:
        logger.error(f"Failed to read audio metadata: {e}")
        return {}


def get_video_metadata(video_path: str) -> Dict[str, Any]:
    """
    Extract metadata from video file (MP4, AVI, MKV, etc.) using hachoir.

    Returns:
        Dictionary with duration, width, height, codec, etc.
    """
    try:
        from hachoir.parser import createParser
        from hachoir.metadata import extractMetadata
    except ImportError:
        logger.error("hachoir is required for video metadata.")
        return {}

    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        parser = createParser(str(path))
        if not parser:
            return {}
        with parser:
            metadata = extractMetadata(parser)
            if not metadata:
                return {}

            result = {}
            for line in metadata.exportPlaintext():
                if ':' in line:
                    key, value = line.split(':', 1)
                    result[key.strip()] = value.strip()

            # Extract specific useful fields
            for attr in ['duration', 'width', 'height', 'frame_rate', 'bit_rate', 'codec']:
                if hasattr(metadata, attr):
                    result[attr] = getattr(metadata, attr)

            return result
    except Exception as e:
        logger.error(f"Failed to read video metadata: {e}")
        return {}