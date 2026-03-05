from app.mocks.mock_youtube import get_mock_captions


def get_mock_transcript(video_id: str) -> str:
    return get_mock_captions(video_id)
