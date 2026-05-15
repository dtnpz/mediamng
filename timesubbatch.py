import os
import re
from datetime import datetime, timedelta

# Regular expression pattern to match timestamps
time_pattern = re.compile(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})')

def adjust_time(timestamp, adjustment):
    # Adjust the timestamp by adding or subtracting the time delay
    adjusted_timestamp = timestamp + timedelta(milliseconds=adjustment)
    return adjusted_timestamp

def process_srt_file(file_path, mode, time_delay):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            subtitles = file.readlines()  # Read lines

            adjusted_subtitles = []
            for line in subtitles:
                match = re.search(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', line)
                if match:
                    start_time, end_time = match.groups()

                    # Extract hours, minutes, seconds, and milliseconds for start time
                    start_hours, start_minutes, start_seconds, start_milliseconds = map(int, re.match(time_pattern, start_time).groups())

                    # Extract hours, minutes, seconds, and milliseconds for end time
                    end_hours, end_minutes, end_seconds, end_milliseconds = map(int, re.match(time_pattern, end_time).groups())

                    # Create datetime objects for start and end times
                    start_timestamp = datetime(1900, 1, 1, start_hours, start_minutes, start_seconds, start_milliseconds * 1000)
                    end_timestamp = datetime(1900, 1, 1, end_hours, end_minutes, end_seconds, end_milliseconds * 1000)

                    # Adjust start and end times based on mode
                    adjusted_start = adjust_time(start_timestamp, -time_delay if mode == 'd' else time_delay)
                    adjusted_end = adjust_time(end_timestamp, -time_delay if mode == 'd' else time_delay)

                    # Format the adjusted timestamps back to the SRT format
                    adjusted_line = f"{adjusted_start.strftime('%H:%M:%S,%f')[:-3]} --> {adjusted_end.strftime('%H:%M:%S,%f')[:-3]}"
                    adjusted_subtitles.append(adjusted_line)
                else:
                    adjusted_subtitles.append(line.strip())

            # Determine the output file path and name
            output_file_path = file_path.replace('.srt', f'_shift{time_delay}ms_{mode}.srt')

            # Write the adjusted subtitles to the new file
            with open(output_file_path, 'w', encoding='utf-8') as output_file:
                output_file.write('\n'.join(adjusted_subtitles))
                print(f"Adjusted subtitles saved to {output_file_path}")
    except FileNotFoundError:
        print("File not found. Please provide a valid file path.")

# Get the current working directory
current_dir = os.getcwd()

# List all SRT files in the current directory
srt_files = [file for file in os.listdir(current_dir) if file.endswith('.srt')]

# Input mode (increase/decrease) and time delay
mode = input("Enter mode ([i]ncrease/[d]ecrease): ")  # "d"
time_delay = int(input("Enter time delay in milliseconds: "))  # 650

# Process each SRT file
for srt_file in srt_files:
    srt_path = os.path.join(current_dir, srt_file)
    process_srt_file(srt_path, mode, time_delay)
