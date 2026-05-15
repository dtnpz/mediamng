import re
import os

def convert_srt_fps(input_file, from_fps=29.97, to_fps=25.0):
    def time_to_ms(h, m, s, ms):
        return ((int(h) * 3600 + int(m) * 60 + int(s)) * 1000) + int(ms)

    def ms_to_time(ms):
        h = ms // 3600000
        ms %= 3600000
        m = ms // 60000
        ms %= 60000
        s = ms // 1000
        ms %= 1000
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    factor = from_fps / to_fps

    def repl(match):
        start_h, start_m, start_s, start_ms, end_h, end_m, end_s, end_ms = match.groups()
        start_ms_total = time_to_ms(start_h, start_m, start_s, start_ms)
        end_ms_total = time_to_ms(end_h, end_m, end_s, end_ms)
        start_new = ms_to_time(int(start_ms_total * factor))
        end_new = ms_to_time(int(end_ms_total * factor))
        return f"{start_new} --> {end_new}"

    with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
        srt_content = f.read()

    time_pattern = r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)"
    converted_content = re.sub(time_pattern, repl, srt_content)

    base, _ = os.path.splitext(input_file)
    output_file = f"{base}_23976.srt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(converted_content)

    print(f"✅ Converted file saved to: {output_file}")


# Ask user for file path
input_file = input("Enter file path: ").strip().strip('"').strip("'")

# Check if file exists before processing
if os.path.isfile(input_file):
    convert_srt_fps(input_file)
else:
    print("❌ File not found. Please check the path and try again.")
