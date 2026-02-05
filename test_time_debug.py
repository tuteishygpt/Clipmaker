
from app.services.subtitle_service import SubtitleService

s = SubtitleService()

def test(sec):
    srt = s.seconds_to_srt_time(sec)
    print(f"Sec: {sec} -> SRT: {srt}")
    back = s.srt_time_to_seconds(srt)
    print(f"Back: {back}")

def test_parse(srt_str):
    sec = s.srt_time_to_seconds(srt_str)
    print(f"Parse '{srt_str}' -> {sec} seconds")
    re_srt = s.seconds_to_srt_time(sec)
    print(f"Re-encode: {re_srt}")

print("Testing seconds_to_srt_time:")
test(23.4)
test(65.5)
test(3665.123)

print("\nTesting parsing weird formats:")
test_parse("00:23:40,00") # From screenshot
test_parse("00:23:40")
test_parse("00:00:23,400")
