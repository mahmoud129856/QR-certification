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
    stream_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    app.logger.addHandler(stream_handler)

    return app

app = create_app()

# =========================
# تسجيل الخط العربي
# =========================
def register_arabic_font():
    """تسجيل خط Amiri-Bold للعربية"""
    try:
        font_path = app.config['FONT_PATH']
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
            app.logger.info(f"✅ تم تسجيل خط Amiri-Bold بنجاح")
            return True
        else:
            app.logger.error(f"❌ خط Amiri-Bold غير موجود في المسار: {font_path}")
            return False
    except Exception as e:
        app.logger.error(f"❌ فشل تسجيل الخط: {str(e)}")
        return False

# تسجيل الخط عند بدء التشغيل
register_arabic_font()

# =========================
# التحقق من الطالب (باستخدام CSV)
# =========================
def verify_student(name):
    """التحقق من الطالب بالاسم فقط باستخدام CSV"""
    try:
        csv_path = app.config['CSV_PATH']
        
        if not os.path.exists(csv_path):
            app.logger.error(f"❌ ملف CSV غير موجود: {csv_path}")
            return False
            
        with open(csv_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                student_name = row.get('Name', '').strip()
                if student_name.upper() == name.strip().upper():
                    app.logger.info(f"✅ تم التحقق من الطالب: {name}")
                    return True
        
        app.logger.warning(f"❌ الطالب غير مسجل: {name}")
        return False
        
    except Exception as e:
        app.logger.error(f"❌ خطأ في التحقق من الطالب: {str(e)}")
        return False

# =========================
# معالجة النص العربي
# =========================
def process_arabic_text(text):
    """معالجة النص العربي للعرض الصحيح"""
    try:
        # إعادة تشكيل الحروف العربية
        reshaped_text = arabic_reshaper.reshape(text)
        # ضبط اتجاه النص
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception as e:
        app.logger.error(f"❌ خطأ في معالجة النص العربي: {str(e)}")
        return text

# =========================
# إنشاء الشهادة (بدعم العربية الكامل)
# =========================
def generate_certificate(name):
    """إنشاء الشهادة مع دعم الأسماء العربية"""
    try:
        # التحقق من وجود ملف القالب
        if not os.path.exists(app.config['TEMPLATE_PATH']):
            app.logger.error(f"❌ ملف القالب غير موجود: {app.config['TEMPLATE_PATH']}")
            return generate_certificate_fallback(name)
        
        # قراءة القالب
        with open(app.config['TEMPLATE_PATH'], "rb") as f:
            template = PdfReader(f)
            page = template.pages[0]

        page_width = float(page.mediabox[2])
        page_height = float(page.mediabox[3])

        # إنشاء طبقة الكتابة
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))

        # التحقق من تسجيل الخط
        font_registered = False
        try:
            # محاولة استخدام الخط العربي المسجل
            can.setFont('ArabicFont', 70)
            font_registered = True
        except:
            # إذا فشل، استخدم خط Helvetica (للكتابة بالإنجليزية فقط)
            app.logger.warning("⚠️ لم يتم العثور على الخط العربي، استخدام Helvetica")
            can.setFont('Helvetica-Bold', 70)

        # معالجة الاسم
        if font_registered:
            # إذا كان الخط عربي، قم بمعالجة النص
            display_name = process_arabic_text(name)
        else:
            # إذا كان الخط إنجليزي، استخدم النص كما هو
            display_name = name

        # تحديد موقع الاسم (عدل هذه القيم حسب قالبك)
        y_pos = 510  # المسافة من أعلى الصفحة
        real_y = page_height - y_pos

        # حساب عرض الاسم وتوسيطه
        text_width = can.stringWidth(display_name, can._fontname, 70)
        x_pos = (page_width - text_width) / 2

        # رسم الاسم
        can.setFillColorRGB(0, 0, 0)  # لون أسود
        can.drawString(x_pos, real_y, display_name)
        can.save()

        # دمج الطبقة مع القالب
        packet.seek(0)
        overlay = PdfReader(packet)

        output = PdfWriter()
        page.merge_page(overlay.pages[0])
        output.add_page(page)

        output_stream = io.BytesIO()
        output.write(output_stream)
        output_stream.seek(0)

        app.logger.info(f"✅ تم إنشاء شهادة لـ: {name}")
        return output_stream

    except Exception as e:
        app.logger.error(f"❌ فشل إنشاء الشهادة: {str(e)}", exc_info=True)
        return generate_certificate_fallback(name)

# =========================
# شهادة بديلة (احتياطي)
# =========================
def generate_certificate_fallback(name):
    """إنشاء شهادة بسيطة بدون قالب"""
    try:
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(595, 842))  # A4
        
        # محاولة استخدام الخط العربي
        try:
            can.setFont('ArabicFont', 50)
            display_name = process_arabic_text(name)
        except:
            can.setFont('Helvetica-Bold', 50)
            display_name = name
        
        # إطار الشهادة
        can.setStrokeColorRGB(0, 0, 0)
        can.rect(50, 50, 495, 742)
        
        # عنوان الشهادة
        can.setFont('Helvetica-Bold', 40)
        can.drawCentredString(297, 700, "CERTIFICATE OF APPRECIATION")
        
        # نص الشهادة
        can.setFont('Helvetica', 20)
        can.drawCentredString(297, 550, "Presented to")
        
        # اسم الطالب
        can.setFont('ArabicFont' if 'ArabicFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold', 45)
        can.drawCentredString(297, 450, display_name)
        
        # باقي النص
        can.setFont('Helvetica', 16)
        can.drawCentredString(297, 350, "In recognition of your valuable participation")
        can.drawCentredString(297, 320, "in the Menoufia Faculty of Engineering Career Fair")
        
        can.save()
        
        packet.seek(0)
        app.logger.info(f"✅ تم إنشاء شهادة احتياطية لـ: {name}")
        return packet
        
    except Exception as e:
        app.logger.error(f"❌ فشل إنشاء الشهادة الاحتياطية: {str(e)}")
        return None

# =========================
# الصفحة الرئيسية
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
            flash("الطالب غير مسجل! يرجى التأكد من الاسم", "error")

    return render_template('form.html')

# =========================
# تحميل الشهادة
# =========================
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

        flash("فشل في إنشاء الشهادة", "error")
        return redirect(url_for('index'))

    except Exception as e:
        app.logger.error(f"❌ خطأ في التحميل: {str(e)}")
        flash("حدث خطأ أثناء إنشاء الشهادة", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()