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
    
    # مسارات الملفات
    app.config['TEMPLATE_PATH'] = os.path.join(BASE_DIR, 'static', 'certificates', 'template.pdf')
    app.config['CSV_PATH'] = os.path.join(BASE_DIR, 'students.csv')
    app.config['FONT_DIR'] = os.path.join(BASE_DIR, 'fonts')
    app.config['FONT_PATH'] = os.path.join(BASE_DIR, 'fonts', 'Amiri-Bold.ttf')
    app.config['BEIN_FONT_PATH'] = os.path.join(BASE_DIR, 'fonts', 'beIN-Normal.ttf')

    app.logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    app.logger.addHandler(stream_handler)

    return app

app = create_app()

# =========================
# تسجيل الخطوط العربية
# =========================
font_registered = False
bein_font_registered = False

# تسجيل خط Amiri
try:
    if os.path.exists(app.config['FONT_PATH']):
        pdfmetrics.registerFont(TTFont('ArabicFont', app.config['FONT_PATH']))
        font_registered = True
        app.logger.info("✅ تم تسجيل خط Amiri-Bold")
    else:
        app.logger.warning("⚠️ خط Amiri غير موجود")
except Exception as e:
    app.logger.warning(f"⚠️ فشل تسجيل Amiri: {e}")

# تسجيل خط beIN Normal
try:
    if os.path.exists(app.config['BEIN_FONT_PATH']):
        pdfmetrics.registerFont(TTFont('BeINFont', app.config['BEIN_FONT_PATH']))
        bein_font_registered = True
        app.logger.info("✅ تم تسجيل خط beIN Normal")
    else:
        app.logger.warning("⚠️ خط beIN Normal غير موجود في: " + app.config['BEIN_FONT_PATH'])
except Exception as e:
    app.logger.warning(f"⚠️ فشل تسجيل beIN Normal: {e}")

# =========================
# التحقق من الطالب
# =========================
def verify_student(name):
    try:
        if not os.path.exists(app.config['CSV_PATH']):
            app.logger.warning("⚠️ ملف CSV غير موجود")
            return False
            
        with open(app.config['CSV_PATH'], 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                student_name = row.get('Name', '').strip()
                if student_name.upper() == name.strip().upper():
                    return True
        return False
    except Exception as e:
        app.logger.error(f"❌ خطأ في قراءة CSV: {e}")
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
# إنشاء الشهادة - بخط beIN Normal واللون البني المحروق
# مع وضع الاسم في المنتصف مائل لليسار قليلاً بنسبة ثابتة
# =========================
def generate_certificate(name):
    template_stream = None
    try:
        # 1. فتح القالب
        template_path = app.config['TEMPLATE_PATH']
        if not os.path.exists(template_path):
            app.logger.error("❌ قالب الشهادة غير موجود")
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
        if bein_font_registered:
            c.setFont('BeINFont', 85)
            display_name = fix_arabic(name)
            app.logger.info("✏️ استخدام خط beIN Normal")
        elif font_registered:
            c.setFont('ArabicFont', 70)
            display_name = fix_arabic(name)
            app.logger.info("✏️ استخدام خط Amiri-Bold")
        else:
            c.setFont('Helvetica-Bold', 70)
            display_name = name
            app.logger.info("✏️ استخدام خط Helvetica")
        
        # 4. موقع الاسم عموديًا (ثابت)
        y_pos = 645
        real_y = page_height - y_pos
        
        # 5. 🎯 حساب الوضع الأفقي الذكي - كل الأسماء بنفس التنسيق
        font_size = 72 if bein_font_registered else 70
        text_width = c.stringWidth(display_name, c._fontname, font_size)
        
        # ✨ نسبة مئوية ثابتة من عرض الاسم (السر في تنسيق موحد)
        offset_percentage = 0.265  # 3% - جرب 0.02 أو 0.04 حسب رغبتك
        offset_left = - (text_width * offset_percentage)
        
        # حساب نقطة البداية: المنتصف + الإزاحة النسبية
        x_pos = (page_width - text_width) / 2 + offset_left
        
        # للتجربة: ظهور قيمة الإزاحة في اللوج
        app.logger.info(f"📐 اسم: {name}, عرض النص: {text_width:.2f}, إزاحة: {offset_left:.2f}, X: {x_pos:.2f}")
        
        # 6. رسم الاسم باللون البني المحروق
        c.setFillColorRGB(0.18, 0.24, 0.41)  # #5C3317
        c.drawString(x_pos, real_y, display_name)
        c.save()
        
        # 7. دمج الطبقات
        packet.seek(0)
        overlay = PdfReader(packet)
        page.merge_page(overlay.pages[0])
        
        # 8. حفظ النتيجة
        output = PdfWriter()
        output.add_page(page)
        
        output_stream = io.BytesIO()
        output.write(output_stream)
        output_stream.seek(0)
        
        app.logger.info(f"✅ تم إنشاء شهادة: {name}")
        return output_stream
        
    except Exception as e:
        app.logger.error(f"❌ فشل إنشاء الشهادة: {str(e)}")
        return None
    finally:
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
            flash("الاسم غير مسجل في قاعدة البيانات!", "error")
            
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
        app.logger.error(f"❌ خطأ في التحميل: {str(e)}")
        flash("حدث خطأ أثناء إنشاء الشهادة", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)