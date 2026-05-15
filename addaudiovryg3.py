import os
import re

def extract_match_number(filename):
    match = re.search(r'EP(\d+)_(\d+)_', filename)  # Extract numbers between underscores
    # match = re.search(r'EP(\d+)\s*\.\w+$', filename)  # Extract numbers between underscores
    # match = re.search(r'EP(\d+)', filename)
    # match = re.search(r'_(\d+)_',filename)
    # match = re.search(r'S(\d{2}E\d{2})', filename)
    # match = re.search(r'_(\d+)', filename)
    # match = re.search(r'EP(\d+)\(\d+\)_(\d+)', filename)
    print(f"Filename: {filename}, Match: {match}")
    print(match,"m")
    if match:
        print(f"Episode Number: {match.group(2)}")
        return match.group(2)
    return None

def extract_language_and_country(filename):
    # parts = os.path.splitext(filename)[0].split('_')
    # last_part = parts[-1]
    # languages = ['ita', 'jpn', 'spa', 'por', 'eng']  # Add more languages as needed
    # for lang in languages:
    #     if lang in last_part:
    #         country = last_part.split(f'-{lang}')[1].capitalize()
    #         return lang.upper(), country.strip('-')
    # # If no language found, set country as language
    # country = last_part.capitalize()
    # return None, country.strip('-')
    print(filename,"fn")
    if len(filename.split('_')) > 1:
        print("this if")
        sepname = filename.split('_')
        
        print(sepname,"sp")
        print(sepname[-1].split('.'),"1")
        prsep = sepname[-1].split('.')
        country = sepname[-2]
        print(country,"ct")
        language = sepname[-1].split('.') if len(filename.split()) > 1 else ' '
        print(language,"lg")
        # acutlang = language[0]+'.'+language[1]
        acutlang = prsep[0]+'.'+prsep[1]
        print(acutlang,"actl")
        return country,acutlang
    else:
        print("this else")
        print(filename,"filename")
        country = os.path.splitext(filename)[0].split('_')[-1][-3:].lower()
        print(country,"ctelse")
        language =''
        return country,language

    

def add_audio_to_video():
    current_dir = os.getcwd()
    video_files = {}
    audio_files = {}

    files = os.listdir(current_dir)

    for filename in files:
        if filename.endswith('.mkv')or filename.endswith('.mp4'):
            match_number = extract_match_number(filename)
            if match_number:
                video_files.setdefault(match_number, []).append(filename)
        elif filename.endswith('.eac3') or filename.endswith('.aac') or filename.endswith('.m4a') or filename.endswith('.opus'):
            match_number = extract_match_number(filename)
            if match_number:
                audio_files.setdefault(match_number, []).append(filename)
        

    for match_number in video_files.keys() & audio_files.keys():
        video_files[match_number].sort()
        audio_files[match_number].sort()

        for video_file in video_files[match_number]:
            output_file = f"{os.path.splitext(video_file)[0]}_waudio{os.path.splitext(video_file)[1]}"
            input_audio_files = ' '.join([f'-i "{audio}"' for audio in audio_files[match_number]])
            
            audio_map_args = ''  # Initialize here

            for i, audio in enumerate(audio_files[match_number]):
                result = extract_language_and_country(audio)
                print(result, "res")
                if len(result) == 2 and len(result[1]) >=3 :
                    language = result[1]
                    print(language,"langres")
                    country = result[0]
                    print(country,"contres")
                    audio_map_args += (
                        f'-map 0:a:0 -metadata:s:a:0  language=jpn '
                        f'-metadata:s:a:0 title="Japanese" '
                        f'-metadata:s:a:0 description="Japanese[2.0]" '
                        f'-map {i+1}:a:0 -metadata:s:a:{i} language={country} '
                        f'-metadata:s:a:{i} title="{language}" '
                        f'-metadata:s:a:{i} description="{language}" '
                    )
                else:
                    country = result[0]
                    audio_map_args += (
                        f'-map 0:a:0 -metadata:s:a:0  language=jpn '
                        f'-metadata:s:a:0 title="Japanese" '
                        f'-metadata:s:a:0 description="Japanese[2.0]" '
                        f'-map {i+1}:a:0 -metadata:s:a:{i} language={country} '
                        f'-metadata:s:a:{i} title="{country}" '
                        f'-metadata:s:a:{i} description="{country}" '
                    )

            cmd = (
                f'ffmpeg -i "{video_file}" {input_audio_files} '
                f'-map 0:v:0 -map 0:s? {audio_map_args} -disposition:a:0 default  '
                f'-c:v copy -c:a copy -c:s copy "{output_file}"'
                
            )
            print(cmd, "cmd")
            os.system(cmd)
            print(f"Audios added to {video_file} as {output_file} with titles from files: {audio_files[match_number]}")


add_audio_to_video()
