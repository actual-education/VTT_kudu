import subprocess
from pathlib import Path

from app.config import settings


class FrameService:
    def extract_frames(self, video_id: str, duration_seconds: int, interval: float = 10.0) -> list[dict]:
        """Extract frames at regular intervals. Returns list of {timestamp, path}."""
        if settings.USE_MOCKS:
            return self._mock_extract(duration_seconds, interval)
        video_path = self._download_video(video_id)
        return self._extract_with_ffmpeg(video_id, video_path, duration_seconds, interval)

    def _mock_extract(self, duration_seconds: int, interval: float) -> list[dict]:
        frames = []
        t = interval
        while t < duration_seconds:
            frames.append({
                "timestamp": t,
                "path": f"/tmp/avce_frames/frame_{t:.1f}.jpg",
            })
            t += interval
        return frames

    def _download_video(self, video_id: str) -> Path:
        cache_dir = Path(settings.VIDEO_CACHE_DIR)
        cache_dir.mkdir(parents=True, exist_ok=True)
        video_path = cache_dir / f"{video_id}.mp4"
        if video_path.exists():
            return video_path

        url = f"https://www.youtube.com/watch?v={video_id}"
        command = [
            settings.YT_DLP_BINARY,
            "--no-playlist",
            "-f",
            "mp4/bestvideo+bestaudio/best",
            "-o",
            str(video_path),
            url,
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(f"yt-dlp not found at '{settings.YT_DLP_BINARY}'") from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            details = stderr or stdout or "Unknown yt-dlp error"
            raise RuntimeError(f"Failed to download source video: {details}") from exc
        return video_path

    def _extract_with_ffmpeg(
        self,
        video_id: str,
        video_path: Path,
        duration_seconds: int,
        interval: float,
    ) -> list[dict]:
        frames_dir = Path(settings.FRAME_OUTPUT_DIR) / video_id
        frames_dir.mkdir(parents=True, exist_ok=True)
        for old_frame in frames_dir.glob("frame_*.jpg"):
            old_frame.unlink()

        frame_pattern = str(frames_dir / "frame_%06d.jpg")
        command = [
            settings.FFMPEG_BINARY,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"fps=1/{interval}",
            frame_pattern,
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(f"ffmpeg not found at '{settings.FFMPEG_BINARY}'") from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            details = stderr or stdout or "Unknown ffmpeg error"
            raise RuntimeError(f"Failed to extract frames: {details}") from exc

        extracted = sorted(frames_dir.glob("frame_*.jpg"))
        if not extracted:
            raise RuntimeError("No frames were extracted from the video")

        frames: list[dict] = []
        for index, frame_path in enumerate(extracted):
            timestamp = round(index * interval, 3)
            if timestamp > duration_seconds:
                break
            frames.append({"timestamp": timestamp, "path": str(frame_path)})
        return frames


frame_service = FrameService()
