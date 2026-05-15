import re

file_path = input("Enter ass file you want to convert PlayRes: " ).strip('"')
yScale = int(input("Enter y scale: "))
# Set scaling factor
scale_x = 1.0  # 1920 stays the same
scale_y = yScale / 1080  # ≈ 0.75556

def scale_pos(match):
    x = int(match.group(1))
    y = int(match.group(2))
    new_x = round(x * scale_x)
    new_y = round(y * scale_y)
    return f"\\pos({new_x},{new_y})"

with open(file_path, 'r', encoding='utf-8') as file:
    lines = file.readlines()

pos_pattern = re.compile(r'\\pos\((\d+),(\d+)\)')
playresy_pattern = re.compile(r'^(PlayResY:\s*)(\d+)', re.IGNORECASE)

file_name, file_extension = file_path.rsplit('.', 1)
new_file_name = f"{file_name}_playres{yScale}.{file_extension}"
# Apply scaling
with open(new_file_name, 'w', encoding='utf-8') as file:
    for line in lines:
        # Update PlayResY line
        if playresy_pattern.match(line):
            line = playresy_pattern.sub(lambda m: f"{m.group(1)}{yScale}", line)

        # Update \pos(x, y) in Dialogue lines
        if line.startswith("Dialogue:") and r"\pos(" in line:
            line = pos_pattern.sub(scale_pos, line)

        file.write(line)

print(f"✅ Done! Output saved to: {new_file_name}")
