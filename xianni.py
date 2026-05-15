import re

def edit_ass_subtitles(input_file, output_file):
    # กำหนดคู่คำที่ต้องการเปลี่ยน (Dictionary)
    # เรียงลำดับจากคำยาวไปคำสั้น หรือคำที่มี "ขั้น" ก่อนเพื่อป้องกันการทับซ้อน
    replacements = {
        "ขั้นหนิงชี่": "ขั้นรวบรวมลมปราณ",
        "หนิงชี่": "รวบรวมลมปราณ",
        
        "ขั้นจู้จี": "ขั้นสร้างรากฐาน",
        "จู้จี": "สร้างรากฐาน",
        
        "ขั้นเจี๋ยตาน": "ขั้นแก่นลมปราณ",
        "เจี๋ยตาน": "แก่นลมปราณ",
        
        "ขั้นหยวนอิง": "ขั้นก่อกำเนิด",
        "หยวนอิง": "ก่อกำเนิด",
        
        "ขั้นฮว่าเสิน": "ขั้นก่อกำเนิด",
        "ฮว่าเสิน": "ก่อกำเนิด",
        
        "ขั้นอิงเปี้ยน": "ขั้นแปลงวิญญาณ",
        "อิงเปี้ยน": "แปลงวิญญาณ",
        
        "ขั้นหยางแท้": "ขั้นรูปธรรมหยาง",
        "หยางแท้": "รูปธรรมหยาง",
        
        "ขั้นหยินเทียม": "ขั้นมายาหยิน",
        "หยินเทียม": "มายาหยิน"
        
    }

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # ทำการแทนที่คำ
        for old_word, new_word in replacements.items():
            content = content.replace(old_word, new_word)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"แก้ไขไฟล์เรียบร้อยแล้ว: {output_file}")

    except FileNotFoundError:
        print("ไม่พบไฟล์ที่ระบุ กรุณาตรวจสอบชื่อไฟล์อีกครั้ง")
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")

# วิธีใช้งาน
input_filename = input("Enter ASS Xianni").strip('"')  # เปลี่ยนเป็นชื่อไฟล์ของคุณ
output_filename = input_filename
edit_ass_subtitles(input_filename, output_filename)