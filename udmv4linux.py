import os
import re
import time
import subprocess
from googletrans import Translator
import pycountry
from natsort import natsorted

def detect_language(file_path):
    max_attempts = 5  # Set maximum attempts
    attempts = 0

    split_filename = os.path.splitext(file_path)[0].split('_')
    platforms = [
        "BiliBiliTH", "Crunchyroll", "AniOneAsia", "ABEMA", "TrueID", "PrimeVideo", "OCR", "Netflix",
        "AniOneThailand[OCR]", "DSNP", "Cockyroll", "iQiyi", "HiDiVE", "Monomax", "trans", "DSNPHS",
        "Shahid", "GGOLL", "3DGuoman", "Laftel", "TrueVisionNow", "PonyCanyonAnime","Flixer","ADN",
        "CatchPlay","FreeReel"
    ]
    platform = f"[{split_filename[-1]}]" if split_filename[-1] in platforms else ""
    # print(split_filename,"spfn")
    # if split_filename[-1] == "BiliBiliTH" or split_filename[-1] == "Crunchyroll"or split_filename[-1] == "AniOneAsia"or split_filename[-1] == "ABEMA"or split_filename[-1] == "TrueID" or split_filename[-1] == "PrimeVideo" or split_filename[-1] == "OCR"or split_filename[-1] == "Netflix"or split_filename[-1] == "AniOneThailand[OCR]"or split_filename[-1] == "DSNP"or split_filename[-1] == "Cockyroll"or split_filename[-1] == "iQiyi"or split_filename[-1] == "HiDiVE"or split_filename[-1] == "Monomax"or split_filename[-1] == "trans"or split_filename[-1] == "DSNPHS" or split_filename[-1] == "Shahid" or split_filename[-1] == "GGOLL" or split_filename[-1] == "3DGuoman" or split_filename[-1] == "Laftel" or split_filename[-1] == "TrueVisionNow" or split_filename[-1] == "PonyCanyonAnime":
        # platform = f"[{split_filename[-1]}]"
        # print(platform,"split")
    # else:
        # print("else platform")
        # platform = ''
    while attempts < max_attempts:
        try:
            file_extension = os.path.splitext(file_path)[1].lower()

            if file_extension == '.ass':
                with open(file_path.strip('"'), 'r', encoding='utf-8') as f:
                    content = f.read()
                    # print(content)

                    # Use regular expressions to remove timestamps and associated information
                    cleaned_content = re.sub(r'^.*?Dialogue: \d+,\d+:\d+:\d+.\d+,\d+:\d+:\d+.\d+,[^,]+,([^,]+,){5}\{[^}]*\}(.*)$', '', content, flags=re.MULTILINE)
                    # print(cleaned_content,"clean")
                    # cleaned_content = re.sub(r'^Dialogue:.*$', '', content, flags=re.MULTILINE)
                    if cleaned_content:  
                        # Clean formatting and tags from the remaining content
                        selected_content = '\n'.join(line.split(',')[-1].strip() for line in cleaned_content.splitlines() if ',' or'{' or '}' in line)
                        # print(selected_content,"SL")
                        use_content = '\n'.join(selected_content.splitlines()[50:70]) if selected_content else None # use_content = selected_content[:500] if content else None 
                        # print(use_content,"UC")
                        if use_content == '':
                            # print("ifff")
                            use_content = '\n'.join(selected_content.splitlines()[13:70])
                            # print(use_content,"ifUC")
                        if use_content:
                            translator = Translator()
                            detected = translator.detect(use_content)
                            # time.sleep(1)
                        if detected:
                            iso_639_1 = detected.lang
                            # print(iso_639_1,"iso639")
                            language = pycountry.languages.get(alpha_2=iso_639_1)
                            if language != None:
                                iso_3166_3 = language.alpha_3
                                cName = language.name
                            else:
                                # print("else")
                                iso_3166_3 = iso_639_1
                                cName = iso_639_1
                            # print(language,"language")
                            # print(cName,"cname")
                            # iso_3166_3 = language.alpha_3 if language != None else iso_639_1
                            # print(iso_639_1)
                            # print("ASS")
                            if cName == "zh-CN":
                                cName = "Chinese Simplified"
                            if cName == "zh-TW":
                                cName = "Chinese Traditional"
                            return iso_3166_3.upper(),cName,platform #if iso_3166_3 != None and cName != None else iso_639_1
                        else:
                            attempts += 1  # Increment attempts if no language detected
                            # time.sleep(1)
                    else:
                        cleaned_content = None
                        attempts += 1  # Increment attempts if no dialogue found
                        # time.sleep(1)
                if cleaned_content == None:
                    # Do something specific when iso_639_1 is None, for example:
                    # print("Language detection failed or iso_639_1 is None")
                    return 'und'  # Return 'und' or any default value when iso_639_1 is None
                return 'und' if use_content == None else None

            elif file_extension == '.srt' or file_extension == '.vtt':
            
                with open(file_path.strip('"'), 'r', encoding='utf-8') as f:
                    content = f.readlines()
                    if file_extension == '.vtt':
                        selected_lines = [line.strip() for i, line in enumerate(content, 1) if i % 3 == 0]
                        selected_line = ''.join(selected_lines) if selected_lines else ''
                        selected_content = selected_line[500:550] if selected_line else ''
                        # print(selected_content, "vtt")
                    else:
                        selected_content = ''.join(content[:50]) if content else ''
                    
                    if selected_content:  
                        translator = Translator()
                        detected = translator.detect(selected_content)
                        # time.sleep(1)
                        # print(detected,"srt")
                        if detected:
                            iso_639_1 = detected.lang
                            # print(iso_639_1,"iso639")
                            language = pycountry.languages.get(alpha_2=iso_639_1)
                            if language != None:
                                iso_3166_3 = language.alpha_3
                                cName = language.name
                            else:
                                # print("else")
                                iso_3166_3 = iso_639_1
                                cName = iso_639_1
                            # print(language,"language")
                            # print(cName,"cname")
                            # iso_3166_3 = language.alpha_3 if language != None else iso_639_1
                            # print(iso_639_1)
                            # print(iso_3166_3,"SRT")
                            if cName == "zh-CN":
                                cName = "Chinese Simplified"
                            if cName == "zh-TW":
                                cName = "Chinese Traditional"
                            return iso_3166_3.upper(),cName,platform #if iso_3166_3 != None and cName != None else iso_639_1
                        else:
                            attempts += 1  

                    else:
                        attempts += 1  
                        
                # print(split_filename,"split_filenamesplit_filename")
                # if split_filename[-2] == "th-TH":
                #     iso_3166_3 = e= "tha" 
                #     cName= "tha" 
                # elif split_filename[-2] == "en-US":
                #     iso_3166_3= "eng" 
                #     cName= "eng" 
                # elif split_filename[-2] == "id-ID":
                #     iso_3166_3= "ind" 
                #     cName= "ind" 
                # elif split_filename[-2] == "ja-JP":
                #     iso_3166_3= "jpn" 
                #     cName= "jpn" 
                # elif split_filename[-2] == "ko-KR":
                #     iso_3166_3= "kor" 
                #     cName= "kor" 
                # elif split_filename[-2] == "ms-MY":
                #     iso_3166_3= "msa" 
                #     cName= "msa" 
                # elif split_filename[-2] == "tl-PH":
                #     iso_3166_3= "tgl" 
                #     cName= "tgl" 
                # elif split_filename[-2] == "vi-VN":
                #     iso_3166_3= "vie" 
                #     cName= "vie" 
                # elif split_filename[-2] == "zh-TW":
                #     iso_3166_3 = "zh-TW" 
                #     cName= "zh-TW" 
                # return iso_3166_3.upper(),cName,platform #if iso_3166_3 != None and cName != None else iso_639_1
                if cleaned_content == None:
                    # Do something specific when iso_639_1 is None, for example:
                    # print("Language detection failed or iso_639_1 is None")
                    return 'und'  # Return 'und' or any default value when iso_639_1 is None
                return 'und','none' if use_content == None else None

            # Add more elif conditions for other file formats if needed

        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            attempts += 1

            if attempts >= max_attempts:
                return localName(file_path)

            continue
    

def localName(file_path):
    platforms = [
    "BiliBiliTH", "Crunchyroll", "AniOneAsia", "ABEMA", "TrueID", "PrimeVideo", "OCR", "Netflix",
    "AniOneThailand[OCR]", "DSNP", "Cockyroll", "iQiyi", "HiDiVE", "Monomax", "trans", "DSNPHS",
    "Shahid", "GGOLL", "3DGuoman", "Laftel", "TrueVisionNow", "PonyCanyonAnime","Flixer","ADN",
    "CatchPlay","FreeReel"
    ]
    splitL, ext = file_path.rsplit(".",1)
    splitname = splitL.split("_")
    print(splitname[-2],"splitname[-2]")
    iso_3166_3 = splitname[-2]
    cName = splitname[-2]
    platform = f"[{splitname[-1]}]" if splitname[-1] in platforms else ""
    return  iso_3166_3.upper(),cName,platform



def detect_subtitle_type(subtitle_files):
    ass_count = 0
    srt_count = 0
    vtt_count = 0
    for subtitle_file in subtitle_files:
        if subtitle_file.endswith(".ass"):
            ass_count += 1
        elif subtitle_file.endswith(".srt"):
            srt_count += 1
        elif subtitle_file.endswith(".vtt"):
            vtt_count += 1


    if ass_count > 0 and srt_count > 0 or vtt_count > 0:
        print(ass_count,srt_count,vtt_count,"count")
        return "both"
    elif ass_count > 0:
        return "ass"
    elif srt_count > 0:
        return "srt"
    elif vtt_count > 0:
        return "vtt"
    else:
        return None

def merge_video_with_subtitle():
    video_extension = ['.mp4', '.mkv', '.ts']
    subtitle_extension = ['.srt', '.ass','.vtt','.sub','.idx']
    video_files = [filename for filename in os.listdir() if any(filename.endswith(ext) for ext in video_extension)]
    subtitle_files = [filename for filename in os.listdir() if any(filename.endswith(ext) for ext in subtitle_extension)]
    subtitle_files = natsorted(subtitle_files)
    print(video_files,"vidddd")
    print(subtitle_files,"subtitle_files")
    font_file_path = r"Arial Unicode MSW.ttf"
    font_caption_path = r"DilleniaUPC.ttf"
    font_file_path_eng = r"Arial Unicode MST.ttf"
    font_th_1 = r"TF Phethai.ttf"
    font_th_2 = r"TF Phethai Ita.ttf"
    font_th_3 = r"NotoSansThai-Thin.ttf"
    font_th_4 = r"NotoSansThai-Regular.ttf"
    font_th_5 = r"Kanit-Regular.ttf"
    for video_file in video_files:
        print(video_file,"in")
        video_name, video_ext = os.path.splitext(video_file)
        print(video_name,"vidname")
        # video_number_match = re.search(r'(\d+)_(\d+)P',video_name,re.IGNORECASE)
        # video_number_match = re.search(r'(\d+)_\d+p_mux',video_name,re.IGNORECASE)
        # video_number_match = re.search(r'(\d{1})-$', video_name, re.IGNORECASE)
        # video_number_match = re.search(r'EP.(\d+)', video_name, re.IGNORECASE)
        # video_number_match = re.search(r'S(\d{2}E\d{2})', video_name, re.IGNORECASE)
        # video_number_match = re.search(r'_(\d+)', video_name, re.IGNORECASE)
        video_number_match = re.search(r'EP(\d+)_(\d+)', video_name, re.IGNORECASE) or re.search(r'EP(\d+)\(\d+\)_(\d+)', video_name,re.IGNORECASE)
        # video_number_match = re.search(r'EP(\d+)\(\d+\)_(\d+)', video_name,re.IGNORECASE)
        # video_number_match = re.search(r'\b\d+\b', video_name, re.IGNORECASE)
        print(video_number_match,"vidmatch")
        if video_number_match:
            print(subtitle_files,"sub ins")
            video_number = video_number_match.group(2)
            print(video_number,"vidnum")
            
            matching_subtitles = [subtitle for subtitle in subtitle_files if f"{video_number}" in subtitle]
            print(matching_subtitles,"matchsub")
            subtitle_type = detect_subtitle_type(matching_subtitles)

            if subtitle_type == "both":
                print("option both")
                option = True
                subtitle_codec = ['-c:s', 'copy']
            elif subtitle_type == "ass":
                print("option ass")
                option = True
                subtitle_codec = ['-c:s', 'ass']
            elif subtitle_type == "srt":
                print("option srt")
                option = True
                subtitle_codec = ['-c:s', 'srt']
            elif subtitle_type == "vtt":
                print("option vtt")
                option = True
                subtitle_codec = ['-c:s', 'copy']
            else:
                print("option else")
                option = False
                subtitle_codec = ['-c:s', 'copy']

            metadata_args = []
            subtitle_track_counter = 0
            subtitle_metadata_counter = 0
            map_options = []

            for subtitle_file in matching_subtitles:
                subtitle_language,subtitle_cname,subPlatform = detect_language(subtitle_file)
                iso_language = subtitle_language
                if subtitle_file.endswith(".ass"):
                    handler_name = f"{subtitle_cname} {subPlatform} : ASS SubRip and modding from web by zrd"
                    title = f"{subtitle_cname} {subPlatform} ASS SubRip and modding from web by zrd"
                elif subtitle_file.endswith(".srt"):
                    handler_name = f"{subtitle_cname} {subPlatform} : SRT SubRip from web by zrd"
                    title = f"{subtitle_cname} {subPlatform} SRT SubRip from web by zrd"
                elif subtitle_file.endswith(".vtt"):
                    handler_name = f"{subtitle_cname} {subPlatform} : VTT SubRip from web by zrd"
                    title = f"{subtitle_cname} {subPlatform} VTT SubRip from web by zrd"
                else:
                    # Handle other subtitle formats if needed
                    continue
                # print(option,"opf")
                output_file = f"{video_name}_sub.mkv"
                
                # subtitle_language = detect_language(subtitle_file)
                # iso_language = subtitle_language
                
                subtitle_track_counter += 1
                map_options.extend([f"-map", f"{subtitle_track_counter}"])

                track_metadata_args = [
                    f'-metadata:s:s:{subtitle_metadata_counter}',
                    f'language={iso_language}',
                    f'-metadata:s:s:{subtitle_metadata_counter}',
                    f'handler_name={handler_name}',
                    f'-metadata:s:s:{subtitle_metadata_counter}',
                    f'title={title}'
                ]
                
                metadata_args.extend(track_metadata_args)
                
                subtitle_metadata_counter += 1
            # print(output_file,"VN")
            subtitle_args = sum([['-i', sub] for sub in matching_subtitles], [])
            if option != False:
                ffmpeg_args = [
                    "ffmpeg","-hide_banner", "-i", video_file
                ] + subtitle_args + [
                    "-map", "0:v:0", "-map", "0:a",
                ] + subtitle_codec + [
                    "-c:v", "copy", "-c:a", "copy",
                ] + map_options+["-disposition:s:0","default"] + metadata_args +[
                    "-attach", font_file_path, "-metadata:s:t", "mimetype=application/x-truetype-font",
                    "-attach", font_file_path_eng,"-metadata:s:t", "mimetype=application/x-truetype-font",
                    "-attach", font_caption_path,"-metadata:s:t", "mimetype=application/x-truetype-font",
                    "-attach", font_th_1,"-metadata:s:t", "mimetype=application/x-truetype-font",
                    "-attach", font_th_2,"-metadata:s:t", "mimetype=application/x-truetype-font",
                    "-attach", font_th_3,"-metadata:s:t", "mimetype=application/x-truetype-font",
                    "-attach", font_th_4,"-metadata:s:t", "mimetype=application/x-truetype-font",
                    "-attach", font_th_5,"-metadata:s:t", "mimetype=application/x-truetype-font"
                    
                ]+ [output_file]
                # "-disposition:a:1","default","-disposition:a:0", "0" ,"-attach", font_file_path_eng,"-metadata:s:t", "mimetype=application/x-truetype-font"
                print(ffmpeg_args, "argsIF") 
                subprocess.run(ffmpeg_args)  
                print(f"Subtitles added to {video_file} successfully as {output_file}")
            else:
                op = video_file.split(".")
                fn = f"{op[0]}_sub.mkv"
                print(fn, "fn")
                ffmpeg_args = [
                    "ffmpeg","-hide_banner", "-i", video_file
                ] + ["-map", "0:v:0", "-map", "0:a",]+ ["-c:v", "copy", "-c:a", "copy",]+[
                    "-attach", font_file_path, "-metadata:s:t", "mimetype=application/x-truetype-font",
                    "-attach", font_file_path_eng,"-metadata:s:t", "mimetype=application/x-truetype-font",
                    "-attach", font_caption_path,"-metadata:s:t", "mimetype=application/x-truetype-font"
                ]+ [fn]
                # "-disposition:a:1","default","-disposition:a:0", "0" ,"-attach", font_file_path_eng,"-metadata:s:t", "mimetype=application/x-truetype-font"
                print(ffmpeg_args, "argsElse") 
                subprocess.run(ffmpeg_args)  
                print(f"Subtitles added to {video_file} successfully as {fn}")

merge_video_with_subtitle()
