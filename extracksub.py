import argparse
import os
import subprocess
import time
from googletrans import Translator
import pycountry

def detect_language(file_path):
    print(file_path, "fp")
    print("in detect_language")
    max_attempts = 5
    attempts = 0

    while attempts < max_attempts:
        try:
            with open(file_path.strip('"'), 'r', encoding='utf-8') as f:
                content = f.read()
                selected_content = '\n'.join(content.splitlines()[50:70]) if content else ''
                print(selected_content, "sl")
                if selected_content:
                    print("sl true")
                    translator = Translator()
                    detected = translator.detect(selected_content)
                    print("bf detect")
                    if detected:
                        print("if detect_language true")
                        iso_639_1 = detected.lang
                        language = pycountry.languages.get(alpha_2=iso_639_1)
                        iso_3166_3 = language.alpha_3 if language else None
                        print(iso_3166_3, "iso_3166_3")
                        return iso_3166_3.upper() if iso_3166_3 else 'UNKNOWN'
                    else:
                        attempts += 1
                else:
                    attempts += 1
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            attempts += 1
    return 'fail'

def extract_subtitle(file_path, platform=""):
    try:
        thai_candidates = [] 
        EngsubFile = []
        new_filepath = ""
        command = f'mkvmerge -i "{file_path}"'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout
        print(output.splitlines())
        subtitle_tracks = []
        for line in output.splitlines():
            if 'subtitles' in line.lower():
                track_info = line.split(':')
                print(track_info, "tif")
                track_id = track_info[0].split()[2]
                print(track_id, "tid")
                subtitle_tracks.append(track_id)
                # print(track_id,"track_id after append")
                # print(subtitle_tracks,"subtitle_tracks after append")
                # print(track_info,"track_info after append")
        # for subtitle_track in subtitle_tracks:
                print(track_info[-1],"TiF2")
                if track_info[-1] == " subtitles (SubStationAlpha)":
                    extfile = 'ass'
                elif track_info[-1] == " subtitles (D_WEBVTT/SUBTITLES)":
                    extfile = 'vtt'
                    continue
                else:
                    extfile = 'srt'
                print(extfile,"extfile")
                extract_command = f"mkvextract tracks \"{file_path}\" {track_id}:\"{file_path.replace('.mkv', f'_{track_id}.{extfile}')}\""
                print(extract_command, "extc")
                subprocess.run(extract_command, shell=True)
                subpath = file_path.replace('.mkv', f'_{track_id}.{extfile}')
                if subpath:
                    print("insubpath")
                    subtitle_language = detect_language(subpath)
                    print("af dt lang")
                    output_file = f"{file_path.replace('.mkv', f'_{track_id}.{extfile}')}".strip('"')
                    if platform != "":
                        if subtitle_language == "tha" or subtitle_language == "THA":
                            new_filepath = f"{file_path.replace('.mkv', f'_{track_id}_{subtitle_language}_{platform}.{extfile}')}".strip('"')
                            os.rename(output_file, new_filepath)
                            size = os.path.getsize(new_filepath)
                            thai_candidates.append((new_filepath, size))
                            if subtitle_language == "eng" or subtitle_language == "ENG":
                                new_filepath = f"{file_path.replace('.mkv', f'_{track_id}_{subtitle_language}_{platform}.{extfile}')}".strip('"')
                                os.rename(output_file, new_filepath)
                                EngsubFile.append((new_filepath))
                            

                            
                        else:
                            new_filepath = f"{file_path.replace('.mkv', f'_{track_id}_{subtitle_language}_{platform}.{extfile}')}".strip('"')
                            os.rename(output_file, new_filepath)
                    else:
                        new_filepath = f"{file_path.replace('.mkv', f'_{track_id}_{subtitle_language}.{extfile}')}".strip('"')
                        os.rename(output_file, new_filepath)
                    

        
                    print(f"Subtitle track {track_id} is language detected as {subtitle_language}. Output filename: {new_filepath}")
        thai_candidates.sort(key=lambda x: x[1], reverse=True)
        print(thai_candidates)
        for index, (new_filepath, size) in enumerate(thai_candidates):
            number = index
            cp = new_filepath.split("_")
            if platform != "":
                tha_filepath = f"{cp[0]}_{cp[1]}_{cp[2]}_{number}_THA_{platform}.{extfile}"
            else:
                tha_filepath = f"{cp[0]}_{cp[1]}_{cp[2]}_{number}_THA.{extfile}"
        tha_filepath = tha_filepath.strip('"')
        os.rename(new_filepath, tha_filepath)
        print(f"Renamed THA size={size} -> {tha_filepath}") 
        
        for index, (new_filepath) in enumerate(EngsubFile):
            print("isitwork?")
            cpe =  new_filepath.split("_")
            engfilepath = f"{cpe[0]}_{cpe[1]}_{cpe[2]}_1_ENG_{platform}.{extfile}"
        eng_filepath = engfilepath.strip('"')
        os.rename(new_filepath,eng_filepath)
        print(f"Renamed Order File={new_filepath} -> {eng_filepath}") 

    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract subtitles from an MKV file and detect language")
    file_path = input("Enter the MKV file path: ")
    parser.add_argument("-n", action="store_true", help="Use _Netflix as the platform")
    parser.add_argument("-a", action="store_true", help="Use _PrimeVideo as the platform")
    parser.add_argument("-c", action="store_true", help="Use _Cockyroll as the platform")
    parser.add_argument("-q", action="store_true", help="Use _IQiyi as the platform")
    parser.add_argument("-d", action="store_true", help="Use _DisneyPlus as the platform")
    parser.add_argument("-l", action="store_true", help="Use _Laftel as the platform")
    parser.add_argument("-H", action="store_true", help="Use _HiDiVE as the platform")
    parser.add_argument("-AD", action="store_true", help="Use _ADN as the platform")
    parser.add_argument("-AB", action="store_true", help="Use _ABEMA as the platform")
    parser.add_argument("-CP", action="store_true", help="Use _CatchPlay as the platform")
    parser.add_argument("-AP", action="store_true", help="Use _AppleTV as the platform")
    args = parser.parse_args()

    # Determine platform based on flags
    platform = ""
    if args.n:
        platform = "Netflix"
    elif args.a:
        platform = "PrimeVideo"
    elif args.c:
        platform = "Cockyroll"
    elif args.q:
        platform = "iQiyi"
    elif args.d:
        platform = "DSNP"
    elif args.l:
        platform = "Laftel"
    elif args.H:
        platform = "HiDiVE"
    elif args.AD:
        platform = "ADN"
    elif args.AB:
        platform = "ABEMA"
    elif args.CP:
        platform = "CatchPlay"
    elif args.AP:
        platform = "AppleTV"
    extract_subtitle(file_path, platform)

