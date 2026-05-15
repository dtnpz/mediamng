import re
import os

def convert_ass_fps(input_file, from_fps=25.0, to_fps=23.976):
    def time_to_ms(h, m, s, cs):
        # ASS uses centiseconds (.xx), not milliseconds (,xxx)
        return ((int(h) * 3600 + int(m) * 60 + float(s)) * 1000) + int(float(cs) * 10)

    def ms_to_time(ms):
        h = int(ms // 3600000)
        ms %= 3600000
        m = int(ms // 60000)
        ms %= 60000
        s = int(ms // 1000)
        cs = int((ms % 1000) / 10)  # centiseconds (2 digits)
        return f"{h}:{m:02}:{s:02}.{cs:02}"

    factor = from_fps / to_fps
    pattern = re.compile(r"^(Dialogue:[^,]*,)(\d+):(\d+):(\d+\.\d+),(\d+):(\d+):(\d+\.\d+)(,.*)", re.MULTILINE)

    def repl(match):
        prefix, sh, sm, ss, eh, em, es, suffix = match.groups()
        start_ms = time_to_ms(sh, sm, ss.split('.')[0], ss.split('.')[1])
        end_ms = time_to_ms(eh, em, es.split('.')[0], es.split('.')[1])
        new_start = ms_to_time(int(start_ms * factor))
        new_end = ms_to_time(int(end_ms * factor))
        return f"{prefix}{new_start},{new_end}{suffix}"

    with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    converted = pattern.sub(repl, content)
    base, _ = os.path.splitext(input_file)
    output_file = f"{base}_23976.ass"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(converted)

    print(f"✅ Converted file saved to: {output_file}")

# --- main ---
input_file = input("Enter .ass file path: ").strip().strip('"').strip("'")
if os.path.isfile(input_file):
    convert_ass_fps(input_file)
else:
    print("❌ File not found. Please check the path and try again.")
