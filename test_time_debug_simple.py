
def srt_time_to_seconds(srt_time):
    srt_time = srt_time.replace(',', '.')
    parts = srt_time.split(':')
    if len(parts) == 3:
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    return 0.0

def seconds_to_srt_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    millis = int((secs % 1) * 1000)
    secs = int(secs)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def test(sec):
    srt = seconds_to_srt_time(sec)
    print(f"Sec: {sec} -> SRT: {srt}")

def test_parse(srt_str):
    sec = srt_time_to_seconds(srt_str)
    print(f"Parse '{srt_str}' -> {sec} seconds")
    re_srt = seconds_to_srt_time(sec)
    print(f"Re-encode: {re_srt}")

print("Testing seconds_to_srt_time:")
test(23.4)
test(65.5)

print("\nTesting parsing weird formats:")
test_parse("00:23:40,00") 
test_parse("00:23:40")
