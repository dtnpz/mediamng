import os
import subprocess
import argparse

def extract_all_audio_streams(input_path, output_path):
    # Get a list of all video files in the input path
    video_files = [f for f in os.listdir(input_path) if f.endswith('.mp4')]

    for video_file in video_files:
        input_file_path = os.path.join(input_path, video_file)

        # Run ffprobe command to get information about audio streams
        ffprobe_command = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=index',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_file_path
        ]

        try:
            ffprobe_output = subprocess.check_output(ffprobe_command, stderr=subprocess.STDOUT, text=True)
            audio_streams = ffprobe_output.strip().split('\n')

            for idx, stream in enumerate(audio_streams):
                stream_index = stream
                print(args,"argsargsargs")
                if  args.e == True:
                    output_file_path = os.path.join(output_path, f"{os.path.splitext(video_file)[0]}_audio_stream{idx}.eac3")
                elif args.a == True:
                    output_file_path = os.path.join(output_path, f"{os.path.splitext(video_file)[0]}_audio_stream{idx}.aac")
                elif args.o == True:
                    output_file_path = os.path.join(output_path, f"{os.path.splitext(video_file)[0]}_audio_stream{idx}.opus")
                else:
                    output_file_path = os.path.join(output_path, f"{os.path.splitext(video_file)[0]}_audio_stream{idx}.mp4")

                # Run ffmpeg command to extract a specific audio stream
                # ffmpeg_command = [
                #     'ffmpeg',
                #     '-i', input_file_path,
                #     '-map', f'0:{stream_index}',
                #     '-c:a', 'libopus', '-b:a','128k',  # Copy the audio stream without re-encoding
                #     output_file_path
                # ]
                ffmpeg_command2 = [
                    'ffmpeg',
                    '-i', input_file_path,
                    '-map', f'0:{stream_index}',
                    '-c:a', 'copy',  # Copy the audio stream without re-encoding
                    output_file_path
                ]
                try:
                    # subprocess.run(ffmpeg_command, check=True)
                    subprocess.run(ffmpeg_command2, check=True)
                    print(f"Audio stream {stream_index} extracted successfully from {video_file}")
                except subprocess.CalledProcessError as e:
                    print(f"Error extracting audio stream {stream_index} from {video_file}: {e}")

        except subprocess.CalledProcessError as e:
            print(f"Error running ffprobe for {video_file}: {e}")

if __name__ == "__main__":
    input_path = input("Enter the path containing video files: ")
    parser = argparse.ArgumentParser(description="Extract subtitles from an MKV file and detect language")
    parser.add_argument("-e", action="store_true", help="Use eac3 as output")
    parser.add_argument("-a", action="store_true", help="Use aac as output")
    parser.add_argument("-o", action="store_true", help="Use opus as output")

    args = parser.parse_args()
    output_path = input_path

    if not os.path.exists(input_path):
        print("Input path does not exist.")
    else:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        extract_all_audio_streams(input_path, output_path)
# v2
# import os
# import subprocess

# def extract_all_audio_streams(input_path, output_path):
#     video_files = [f for f in os.listdir(input_path) if f.endswith('.mkv')]

#     for video_file in video_files:
#         input_file_path = os.path.join(input_path, video_file)

#         ffprobe_command = [
#             'ffprobe',
#             '-v', 'error',
#             '-select_streams', 'a',
#             '-show_entries', 'stream=index:stream_tags=language:stream_tags=title',
#             '-of', 'default=noprint_wrappers=1:nokey=1',
#             input_file_path
#         ]

#         try:
#             ffprobe_output = subprocess.check_output(ffprobe_command, stderr=subprocess.STDOUT, text=True)
#             print(ffprobe_output,"probe")
#             audio_streams = ffprobe_output.strip().split('\n')
#             print(audio_streams,"full")
#             audio_dict = {}
#             i = 0
#             while i < len(audio_streams) - 1:
#                 key = audio_streams[i]
#                 value = ''
#                 i += 1
#                 while i < len(audio_streams) and not audio_streams[i].isdigit():
#                     value += audio_streams[i]
#                     i += 1
#                     if i < len(audio_streams) and not audio_streams[i].isdigit():
#                         value += '-'
#                 audio_dict[key] = value

#             print(audio_dict)
#             list_length = len(audio_streams)
#             dict_length = len(audio_dict)
#             print(list_length,"list","\n",dict_length,"dict")
#             print()
#             for idx, stream_info in enumerate(audio_dict):
#                 stream_data = stream_info.split('|')

#                 stream_index = stream_data[0]

#                 if len(audio_dict) > 2:
#                     print(str(idx+1),"idx")
#                     stream_language = audio_dict.get(str(idx+1))
#                     print(stream_language,"bfffflang")
#                     if len(stream_language)>1:
#                         stream_language.split('-')
#                     print(stream_language,"lang")
#                     output_language = stream_language if stream_language[0] else f"stream{idx+1}"
#                     output_title = stream_language if stream_language[0] else None
#                 else:
#                     output_language = f"stream{idx}"

#                 output_file_path = os.path.join(output_path, f"{os.path.splitext(video_file)[0]}_track{idx+1}_{output_language}.eac3")
#                 # print(output_file_path,"fp")
#                 aorder = idx+1
#                 if output_title == None:
#                     ffmpeg_command = [
#                         'ffmpeg',
#                         '-i', input_file_path,
#                         '-map', f'0:{stream_index}',
#                         '-c:a', 'copy',
#                         f'-metadata:s:a:0',
#                         f'language={stream_language}',
#                         output_file_path
#                     ]
#                 else:
#                     ffmpeg_command = [
#                         'ffmpeg',
#                         '-i', input_file_path,
#                         '-map', f'0:{stream_index}',
#                         '-c:a', 'copy',
#                         f'-metadata:s:a:0',
#                         f'language={stream_language}',
#                         f'-metadata:s:a:0',
#                         f'title={output_title}',
#                         output_file_path
#                     ]
#                 print(ffmpeg_command,"cmd")
#                 try:
#                     subprocess.run(ffmpeg_command, check=True)
#                     print(f"Audio stream {stream_index} extracted successfully from {video_file}")
#                 except subprocess.CalledProcessError as e:
#                     print(f"Error extracting audio stream {stream_index} from {video_file}: {e}")

#         except subprocess.CalledProcessError as e:
#             print(f"Error running ffprobe for {video_file}: {e}")

# if __name__ == "__main__":
#     input_path = input("Enter the path containing video files: ")
#     output_path = input_path

#     if not os.path.exists(input_path):
#         print("Input path does not exist.")
#     else:
#         if not os.path.exists(output_path):
#             os.makedirs(output_path)

#         extract_all_audio_streams(input_path, output_path)

