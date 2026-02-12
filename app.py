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
    app.logger.addHandler(stream_handler)

    return app

app = create_app()

# =========================
# تسجيل الخط العربي (مرة واحدة)
# =========================
try:
    if os.path.exists(app.config['FONT_PATH']):
        pdfmetrics.registerFont(TTFont('ArabicFont', app.config['FONT_PATH']))
        app.logger.info("✅ خط Amiri-Bold جاهز")
    else:
        app.logger.error("❌ الخط مش موجود!")
except Exception as e:
    app.logger.error(f"❌ خطأ في تسجيل الخط: {e}")

# =========================
# التحقق من الطالب
# =========================
def verify_student(name):
    try:
        with open(app.config['CSV_PATH'], 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Name', '').strip().upper() == name.strip().upper():
                    return True
        return False
    except Exception as e:
        app.logger.error(f"❌ خطأ في التحقق: {e}")
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
# إنشاء الشهادة (القالب بتاعك بالظبط)
# =========================
def generate_certificate(name):
    try:
        # 1. افتح القالب بتاعك
        with open(app.config['TEMPLATE_PATH'], 'rb') as f:
            template = PdfReader(f)
            page = template.pages[0]
        
        page_width = float(page.mediabox[2])
        page_height = float(page.mediabox[3])
        
        # 2. أنشئ طبقة الكتابة
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))
        
        # 3. استخدم الخط العربي
        c.setFont('ArabicFont', 70)  # الحجم بتاعك 70
        c.setFillColorRGB(0, 0, 0)    # لون أسود
        
        # 4. مكان الاسم بتاعك بالظبط
        y_pos = 510
        real_y = page_height - y_pos
        
        # 5. الاسم بعد التعديل
        arabic_name = fix_arabic(name)
        
        # 6. توسيط الاسم
        text_width = c.stringWidth(arabic_name, 'ArabicFont', 70)
        x_pos = (page_width - text_width) / 2
        
        # 7. اكتب الاسم على القالب
        c.drawString(x_pos, real_y, arabic_name)
        c.save()
        
        # 8. دمج الطبقة مع القالب
        packet.seek(0)
        overlay = PdfReader(packet)
        
        output = PdfWriter()
        page.merge_page(overlay.pages[0])
        output.add_page(page)
        
        # 9. تسليم الشهادة
        output_stream = io.BytesIO()
        output.write(output_stream)
        output_stream.seek(0)
        
        app.logger.info(f"✅ تم إنشاء شهادة: {name}")
        return output_stream
        
    except Exception as e:
        app.logger.error(f"❌ فشل إنشاء الشهادة: {e}")
        return None

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
            flash("الطالب غير مسجل!", "error")
    return render_template('form.html')

@app.route('/download', methods=['POST'])
def download_certificate():
    try:
        name = request.form.get('name', '').strip()
        certificate = generate_certificate(name)
        
        if certificate:
            return send_file(
                certificate,
                as_attachment=True,
                download_name=f"Certificate_{name.replace(' ', '_')}.pdf",
                mimetype='application/pdf'
            )
        
        flash("فشل في إنشاء الشهادة", "error")
        return redirect(url_for('index'))
        
    except Exception as e:
        app.logger.error(f"❌ خطأ: {e}")
        flash("حدث خطأ", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()