import os
import re

# New header content
new_header = """[Script Info]
Title: ไทย
Original Script: คำบรรยายโดย cr_th
Original Translation: คำบรรยายโดย cr_th
Original Editing: zared
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
Timer: 0.0000
WrapStyle: 0


[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Unicode MS,85,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3.8,0,2,15,15,110,1
Style: OS,Arial Unicode MS,85,&H00FFFFFF,&H0000FFFF,&H00000000,&H7F404040,-1,0,0,0,100,100,0,0,1,6,3,8,3,3,110,0
Style: Italics,Arial Unicode MS,85,&H00FFFFFF,&H0000FFFF,&H00000000,&H7F404040,-1,-1,0,0,100,100,0,0,1,6,3,2,60,60,110,0
Style: On Top,Arial Unicode MS,85,&H00FFFFFF,&H0000FFFF,&H00000000,&H7F404040,-1,0,0,0,100,100,0,0,1,6,3,8,60,60,80,0
Style: DefaultLow,Arial Unicode MS,85,&H00FFFFFF,&H0000FFFF,&H00000000,&H7F404040,-1,0,0,0,100,100,0,0,1,6,3,2,60,60,55,0
"""

def process_dialogue_line(line: str) -> str:
    # remove {\an0-9} except {\an8}
    line = re.sub(r"\{\\an[0-79]\}", "", line)

    if ",," not in line:
        return line

    head, text = line.rsplit(",,", 1)
    t = text.strip()

    # if text starts with ( and ends with )
    if t.startswith("(") and t.endswith(")"):
        # remove any remaining alignment tags
        head = re.sub(r"\{\\an\d+\}", "", head)
        line = head + ",,{\\an8}" + text

    return line


# Loop through all files
for filename in os.listdir():
    if "THA_Cockyroll.ass" in filename:
        print(f"Processing {filename} ...")

        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace header
        parts = re.split(r"\[Events\]", content, maxsplit=1)
        if len(parts) == 2:
            content = f"{new_header}\n\n[Events]{parts[1]}"
        else:
            print(f"⚠️ Warning: [Events] not found in {filename}, skipped header replace.")
            continue

        # Replace alignment styles
        content = content.replace("BottomCenter", "Default")
        content = content.replace("TopCenter", "On Top")

        # Fix Thai spacing before "ๆ"
        content = re.sub(r"\sๆ", "ๆ", content)

        content = content.replace(r"\n", r"\N")
        # -------------------------------------------------------------------

        # ---- NEW FEATURE: process Dialogue lines ----
        lines = content.splitlines()
        new_lines = []

        for line in lines:
            if line.startswith("Dialogue:"):
                line = process_dialogue_line(line)
            new_lines.append(line)

        content = "\n".join(new_lines)
        # --------------------------------------------

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ Finished {filename}")

print("✅ All done!")