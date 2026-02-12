from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import io
import os
import logging
import sys
import csv

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-123')

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    app.config['TEMPLATE_PATH'] = os.path.join(BASE_DIR, 'static', 'certificates', 'template.pdf')
    app.config['CSV_PATH'] = os.path.join(BASE_DIR, 'students.csv')
    app.config['FONT_PATH'] = os.path.join(BASE_DIR, 'fonts', 'Amiri-Bold.ttf')

    app.logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    app.logger.addHandler(stream_handler)

    return app

app = create_app()

# =========================
# تسجيل الخط العربي
# =========================
font_registered = False
try:
    if os.path.exists(app.config['FONT_PATH']):
        pdfmetrics.registerFont(TTFont('ArabicFont', app.config['FONT_PATH']))
        font_registered = True
        app.logger.info("✅ تم تسجيل خط Amiri-Bold")
    else:
        app.logger.warning("⚠️ الخط غير موجود - استخدام Helvetica")
except Exception as e:
    app.logger.warning(f"⚠️ فشل تسجيل الخط: {e}")

# =========================
# التحقق من الطالب
# =========================
def verify_student(name):
    try:
        if not os.path.exists(app.config['CSV_PATH']):
            return False
            
        with open(app.config['CSV_PATH'], 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                student_name = row.get('Name', '').strip()
                if student_name.upper() == name.strip().upper():
                    return True
        return False
    except:
        return False

# =========================
# معالجة النص العربي
# =========================
def fix_arabic(text):
    try:
        return get_display(arabic_reshaper.reshape(text))
    except:
        return text

# =========================
# إنشاء الشهادة - النسخة النهائية اللي بتشتغل 100%
# =========================
def generate_certificate(name):
    template_stream = None
    try:
        # 1. فتح القالب وقراءته مرة واحدة
        template_path = app.config['TEMPLATE_PATH']
        if not os.path.exists(template_path):
            app.logger.error("❌ القالب غير موجود")
            return None
            
        with open(template_path, 'rb') as f:
            template_bytes = f.read()
        
        template_stream = io.BytesIO(template_bytes)
        template = PdfReader(template_stream)
        page = template.pages[0]
        
        page_width = float(page.mediabox[2])
        page_height = float(page.mediabox[3])
        
        # 2. إنشاء طبقة الكتابة
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))
        
        # 3. إعدادات النص
        if font_registered:
            c.setFont('ArabicFont', 70)
            display_name = fix_arabic(name)
        else:
            c.setFont('Helvetica-Bold', 70)
            display_name = name
        
        # 4. موقع الاسم (مضبوط زي ما انت عايز)
        y_pos = 413
        real_y = page_height - y_pos
        
        # 5. توسيط الاسم
        text_width = c.stringWidth(display_name, c._fontname, 70)
        x_pos = (page_width - text_width) / 2
        
        # 6. رسم الاسم
        c.setFillColorRGB(0, 0, 0)
        c.drawString(x_pos, real_y, display_name)
        c.save()
        
        # 7. قراءة طبقة الكتابة
        packet.seek(0)
        overlay = PdfReader(packet)
        
        # 8. دمج الطبقات
        output = PdfWriter()
        page.merge_page(overlay.pages[0])
        output.add_page(page)
        
        # 9. حفظ النتيجة
        output_stream = io.BytesIO()
        output.write(output_stream)
        output_stream.seek(0)
        
        app.logger.info(f"✅ تم إنشاء شهادة: {name}")
        return output_stream
        
    except Exception as e:
        app.logger.error(f"❌ فشل إنشاء الشهادة: {str(e)}")
        return None
    finally:
        # التأكد من قفل الملفات
        if template_stream:
            template_stream.close()

# =========================
# Routes
# =========================
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        
        if not name:
            flash("يجب إدخال اسم الطالب", "error")
            return redirect(url_for('index'))
            
        if verify_student(name):
            return render_template('certificate_ready.html', name=name)
        else:
            flash("الاسم غير مسجل!", "error")
            
    return render_template('form.html')

@app.route('/download', methods=['POST'])
def download_certificate():
    try:
        name = request.form.get('name', '').strip()
        
        if not name:
            flash("اسم الطالب مطلوب", "error")
            return redirect(url_for('index'))
        
        certificate = generate_certificate(name)
        
        if certificate:
            filename = f"Certificate_{name.replace(' ', '_')}.pdf"
            return send_file(
                certificate,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        else:
            flash("فشل في إنشاء الشهادة - تأكد من وجود ملف القالب", "error")
            return redirect(url_for('index'))
            
    except Exception as e:
        app.logger.error(f"❌ خطأ: {str(e)}")
        flash("حدث خطأ", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()