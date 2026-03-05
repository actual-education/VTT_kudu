import pytest

from app.mocks.mock_youtube import extract_video_id


class TestExtractVideoId:
    def test_extracts_watch_url(self):
        video_id = extract_video_id("https://www.youtube.com/watch?v=ZM8ECpBuQYE")
        assert video_id == "ZM8ECpBuQYE"

    def test_extracts_short_url(self):
        video_id = extract_video_id("https://youtu.be/ZM8ECpBuQYE?si=abc123")
        assert video_id == "ZM8ECpBuQYE"

    def test_extracts_shorts_url(self):
        video_id = extract_video_id("https://www.youtube.com/shorts/ZM8ECpBuQYE")
        assert video_id == "ZM8ECpBuQYE"

    def test_rejects_non_youtube_url(self):
        with pytest.raises(ValueError, match="Cannot extract YouTube video ID"):
            extract_video_id("https://example.com/video/ZM8ECpBuQYE")
