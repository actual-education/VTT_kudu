import pytest
from app.utils.vtt_parser import (
    parse_vtt,
    generate_vtt,
    validate_vtt,
    parse_vtt_timestamp,
    format_vtt_timestamp,
    VttCue,
)
from app.utils.srt_parser import parse_srt, srt_to_vtt


class TestTimestampParsing:
    def test_parse_hh_mm_ss_ms(self):
        assert parse_vtt_timestamp("00:01:30.500") == 90.5

    def test_parse_mm_ss_ms(self):
        assert parse_vtt_timestamp("01:30.500") == 90.5

    def test_parse_zero(self):
        assert parse_vtt_timestamp("00:00:00.000") == 0.0

    def test_parse_hours(self):
        assert parse_vtt_timestamp("01:00:00.000") == 3600.0

    def test_format_simple(self):
        assert format_vtt_timestamp(90.5) == "00:01:30.500"

    def test_format_zero(self):
        assert format_vtt_timestamp(0.0) == "00:00:00.000"

    def test_format_hours(self):
        assert format_vtt_timestamp(3661.123) == "01:01:01.123"

    def test_roundtrip(self):
        ts = "00:05:30.250"
        assert format_vtt_timestamp(parse_vtt_timestamp(ts)) == ts


class TestParseVtt:
    SAMPLE_VTT = """WEBVTT

00:00:00.000 --> 00:00:05.000
Hello world

00:00:05.000 --> 00:00:10.000
Second cue here

00:00:10.000 --> 00:00:15.000
Third cue
with two lines
"""

    def test_parse_basic(self):
        cues = parse_vtt(self.SAMPLE_VTT)
        assert len(cues) == 3
        assert cues[0].text == "Hello world"
        assert cues[0].start_time == 0.0
        assert cues[0].end_time == 5.0

    def test_parse_multiline_cue(self):
        cues = parse_vtt(self.SAMPLE_VTT)
        assert cues[2].text == "Third cue\nwith two lines"

    def test_parse_with_identifiers(self):
        vtt = """WEBVTT

1
00:00:00.000 --> 00:00:05.000
First cue

2
00:00:05.000 --> 00:00:10.000
Second cue
"""
        cues = parse_vtt(vtt)
        assert len(cues) == 2
        assert cues[0].identifier == "1"
        assert cues[1].identifier == "2"

    def test_parse_empty(self):
        cues = parse_vtt("WEBVTT\n\n")
        assert len(cues) == 0

    def test_parse_with_header_metadata(self):
        vtt = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:05.000
Hello
"""
        cues = parse_vtt(vtt)
        assert len(cues) == 1
        assert cues[0].text == "Hello"

    def test_strips_youtube_inline_timestamp_and_class_tags(self):
        vtt = """WEBVTT

00:00:45.180 --> 00:00:47.209
the specific direction so<00:00:45.540><c> while</c><00:00:45.719><c> X</c>
"""
        cues = parse_vtt(vtt)
        assert len(cues) == 1
        assert "<00:" not in cues[0].text
        assert "<c>" not in cues[0].text
        assert "</c>" not in cues[0].text
        assert cues[0].text == "the specific direction so while X"


class TestGenerateVtt:
    def test_generate_basic(self):
        cues = [
            VttCue(start_time=0.0, end_time=5.0, text="Hello"),
            VttCue(start_time=5.0, end_time=10.0, text="World"),
        ]
        vtt = generate_vtt(cues)
        assert vtt.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:05.000" in vtt
        assert "Hello" in vtt
        assert "World" in vtt

    def test_generate_with_identifiers(self):
        cues = [VttCue(start_time=0.0, end_time=5.0, text="Hello", identifier="1")]
        vtt = generate_vtt(cues)
        assert "1\n00:00:00.000" in vtt

    def test_roundtrip(self):
        original_cues = [
            VttCue(start_time=0.0, end_time=5.0, text="First"),
            VttCue(start_time=5.0, end_time=10.0, text="Second"),
            VttCue(start_time=10.0, end_time=15.0, text="Third"),
        ]
        vtt = generate_vtt(original_cues)
        parsed = parse_vtt(vtt)
        assert len(parsed) == 3
        for orig, parsed_cue in zip(original_cues, parsed):
            assert orig.start_time == parsed_cue.start_time
            assert orig.end_time == parsed_cue.end_time
            assert orig.text == parsed_cue.text


class TestValidateVtt:
    def test_valid_cues(self):
        cues = [
            VttCue(start_time=0.0, end_time=5.0, text="Hello"),
            VttCue(start_time=5.0, end_time=10.0, text="World"),
        ]
        errors = validate_vtt(cues)
        assert errors == []

    def test_end_before_start(self):
        cues = [VttCue(start_time=5.0, end_time=3.0, text="Bad")]
        errors = validate_vtt(cues)
        assert len(errors) == 1
        assert "end_time" in errors[0]

    def test_empty_text(self):
        cues = [VttCue(start_time=0.0, end_time=5.0, text="")]
        errors = validate_vtt(cues)
        assert len(errors) == 1
        assert "empty" in errors[0]

    def test_non_monotonic(self):
        cues = [
            VttCue(start_time=5.0, end_time=10.0, text="First"),
            VttCue(start_time=3.0, end_time=8.0, text="Second"),
        ]
        errors = validate_vtt(cues)
        assert any("previous start_time" in e for e in errors)

    def test_overlap(self):
        cues = [
            VttCue(start_time=0.0, end_time=6.0, text="First"),
            VttCue(start_time=5.0, end_time=10.0, text="Second"),
        ]
        errors = validate_vtt(cues)
        assert any("overlaps" in e for e in errors)


class TestParseSrt:
    SAMPLE_SRT = """1
00:00:00,000 --> 00:00:05,000
Hello world

2
00:00:05,000 --> 00:00:10,000
Second cue

3
00:00:10,000 --> 00:00:15,000
Third cue
with two lines
"""

    def test_parse_basic(self):
        cues = parse_srt(self.SAMPLE_SRT)
        assert len(cues) == 3
        assert cues[0].text == "Hello world"
        assert cues[0].start_time == 0.0
        assert cues[0].end_time == 5.0

    def test_parse_multiline(self):
        cues = parse_srt(self.SAMPLE_SRT)
        assert cues[2].text == "Third cue\nwith two lines"

    def test_identifiers(self):
        cues = parse_srt(self.SAMPLE_SRT)
        assert cues[0].identifier == "1"
        assert cues[1].identifier == "2"

    def test_srt_to_vtt_conversion(self):
        vtt = srt_to_vtt(self.SAMPLE_SRT)
        assert vtt.startswith("WEBVTT")
        assert "00:00:05.000" in vtt
        cues = parse_vtt(vtt)
        assert len(cues) == 3
