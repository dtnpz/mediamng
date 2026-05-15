import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def time_to_frame(ass_time, fps=23.976):
    """
    แปลงเวลาของไฟล์ ASS (H:MM:SS.cc) เป็นหมายเลขเฟรม
    """
    parts = ass_time.split(':')
    h = int(parts[0])
    m = int(parts[1])
    s_parts = parts[2].split('.')
    s = int(s_parts[0])
    cs = int(s_parts[1])
    
    # คำนวณเป็นวินาทีทั้งหมด
    total_seconds = h * 3600 + m * 60 + s + (cs / 100.0)
    tts = total_seconds
    # แปลงเป็นหมายเลขเฟรม (ใช้ round เพื่อปัดเศษไปยังเฟรมที่ใกล้เคียงที่สุด)
    print(parts,tts * fps,total_seconds,fps,"",int(round(tts * fps)))
    return int(tts * fps)

def writeASS(original_line, new_text, finalASSFile):
    """
    แทรกข้อความที่ได้จาก OCR กลับเข้าไปในบรรทัดเดิมและเขียนลงไฟล์
    """
    parts = original_line.strip().split(',', 9)
    if len(parts) == 10:
        # แทนที่การขึ้นบรรทัดใหม่ด้วย \N ตามมาตรฐาน ASS
        clean_text = new_text.replace('\n', '\\N').strip()
        new_line = ','.join(parts[:9]) + ',' + clean_text + '\n'
    else:
        new_line = original_line + '\n'
        
    with open(finalASSFile, 'a', encoding='utf-8') as f:
        f.write(new_line)

def OCR(img, driver):
    """
    ส่งภาพไปที่ Google Translate และ Return ข้อความกลับมา (แทนการเขียนลงไฟล์ตรงๆ)
    """
    if not os.path.exists(img):
        return None # คืนค่า None เพื่อบอกว่าไม่พบไฟล์ภาพ

    driver.get("https://translate.google.com/?sl=zh-CN&tl=en&op=images")
    
    try:
        # กดปุ่มเคลียร์รูปเก่า (ถ้ามี)
        button = driver.find_element(By.XPATH, "//*[@id='yDmH0d']/c-wiz/div/div/div/div[2]/div[1]/div[3]/div[1]/div[1]/form[2]/div/div/button/span")
        button.click()
        driver.refresh()
        time.sleep(1)
    except Exception:
        pass
        
    try:
        # รอจนกว่าช่องอัปโหลดจะพร้อมใช้งาน
        input_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".r83qMb .ZdLswd"))
        )
        print(f"\nกำลังประมวลผล: {os.path.basename(img)}")
        input_element.send_keys(img)

        # รอให้ภาพที่มี src เริ่มต้นด้วย blob โหลดเสร็จ (แสดงว่าอัปโหลดและเริ่มแปลแล้ว)
        img_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//img[starts-with(@src, 'blob')]"))
        )
        
        # Google Translate จะใช้เวลาแป๊บเดียวในการอัปเดตค่า alt เป็นข้อความแปล
        time.sleep(2) 
        alt_text = img_element.get_attribute("alt")
        
        # วนลูปเช็คเผื่อระบบยังแปลไม่เสร็จ (alt_text จะยังว่าง หรือเป็นค่าเริ่มต้น)
        retries = 5
        while (not alt_text or alt_text == "Image translation") and retries > 0:
            time.sleep(1)
            alt_text = img_element.get_attribute("alt")
            retries -= 1

        # ถ้าจบการรอแล้วข้อยังคงเป็นค่า default ถือว่าว่างเปล่า
        if not alt_text or alt_text == "Image translation":
            return ""
            
        return alt_text
        
    except Exception as e:
        print(f"เกิดข้อผิดพลาดกับรูป {img}: {e}")
        return ""

def process_subtitle_batch(input_ass, output_txt, img_folder, fps, driver):
    """
    อ่านไฟล์ ASS คัดกรองบรรทัดว่าง และรัน Process
    """
    # เคลียร์ไฟล์ Output ใหม่ทุกครั้งที่เริ่มรัน
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write("")

    with open(input_ass, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        if line.startswith("Dialogue:"):
            # ASS Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
            # แบ่ง string ด้วยลูกน้ำ 9 ครั้ง เพื่อแยกส่วนประกอบทั้งหมด
            parts = line.strip().split(',', 9)
            if len(parts) == 10:
                text_content = parts[9].strip()
                
                # ตรวจสอบว่าเป็นบรรทัดที่ไม่มีข้อความ (Null text line)
                if not text_content:
                    start_time = parts[1]
                    frame_num = time_to_frame(start_time, fps)
                    
                    # วนลูปเช็คจนกว่าจะได้ข้อความที่ไม่ใช่ค่าว่าง
                    while True:
                        img_filename = f"{frame_num:08d}.jpg"
                        img_path = os.path.join(img_folder, img_filename)
                        
                        # ป้องกัน Infinite Loop ในกรณีที่ขยับเฟรมไปเรื่อยๆ จนหลุดโฟลเดอร์รูปภาพ
                        if not os.path.exists(img_path):
                            print(f"หยุดค้นหา: ไม่พบไฟล์ภาพ {img_filename} อีกต่อไป")
                            writeASS(line, "", output_txt)
                            break
                            
                        alt_text = OCR(img_path, driver)
                        
                        if alt_text is None:
                            # เกิด error ไฟล์ไม่มี (ถูกดักไว้ในฟังก์ชัน OCR)
                            writeASS(line, "", output_txt)
                            break
                            
                        if alt_text: # มีข้อความกลับมา
                            print(f"ผลลัพธ์ OCR: {alt_text}")
                            writeASS(line, alt_text, output_txt)
                            break # หลุดออกจากลูป While เพื่อไปบรรทัด Dialogue ถัดไป
                        else:
                            print(f"รูป {img_filename} ค่าเป็นว่างเปล่า -> เลื่อนไปหาในเฟรมถัดไป (+4)")
                            frame_num += 4 
                else:
                    # ถ้ามีข้อความอยู่แล้ว ให้เขียนลงไฟล์ได้เลยโดยไม่ต้องทำอะไร
                    with open(output_txt, 'a', encoding='utf-8') as out_f:
                        out_f.write(line)
            else:
                # กรณีโครงสร้าง Dialogue ผิดเพี้ยน
                with open(output_txt, 'a', encoding='utf-8') as out_f:
                    out_f.write(line)
        else:
            # เก็บโครงสร้าง Header และ Style ของไฟล์ ASS ไว้ทั้งหมด
            with open(output_txt, 'a', encoding='utf-8') as out_f:
                out_f.write(line)

if __name__ == "__main__":
    # ----------------------------------------
    # การตั้งค่า (Configuration)
    # ----------------------------------------
    INPUT_ASS_FILE = "/datadisk/daily/gm/aod04.ass"   
    OUTPUT_TXT_FILE = "aod04v2.ass"
    IMAGE_FOLDER = "/diskdata/winbackup/Desktop/mpd/subex/taod04"
    FRAME_RATE = 23.976

    # ----------------------------------------
    # การเชื่อมต่อ WebDriver
    # ----------------------------------------
    ChromeDriver = "/usr/bin/chromedriver"
    services = Service(ChromeDriver)
    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", "localhost:4144")
    
    print("กำลังเชื่อมต่อกับ Chrome Debugger...")
    driver = webdriver.Chrome(options=options, service=services)
    
    print("เริ่มการประมวลผลไฟล์...")
    process_subtitle_batch(INPUT_ASS_FILE, OUTPUT_TXT_FILE, IMAGE_FOLDER, FRAME_RATE, driver)
    print("เสร็จสิ้นการทำงาน!")