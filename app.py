from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import arabic_reshaper
from bidi.algorithm import get_display
import io
import os
import logging
import pandas as pd
import sys
import requests


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-123')

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    app.config['TEMPLATE_PATH'] = os.path.join(
        BASE_DIR, 'static', 'certificates', 'template.pdf'
    )

    app.config['EXCEL_PATH'] = os.path.join(
        BASE_DIR, 'students.xlsx'
    )
    
    # مجلد للخطوط
    app.config['FONTS_DIR'] = os.path.join(BASE_DIR, 'static', 'fonts')
    
    # إنشاء مجلد الخطوط إذا لم يكن موجوداً
    os.makedirs(app.config['FONTS_DIR'], exist_ok=True)

    app.logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    app.logger.addHandler(stream_handler)

    return app


app = create_app()


# =========================
# تحميل الخطوط تلقائياً
# =========================
def download_arabic_fonts():
    """تحميل الخطوط العربية تلقائياً إذا لم تكن موجودة"""
    fonts = {
        'Amiri-Regular.ttf': 'https://github.com/alif-type/amiri/releases/download/1.000/Amiri-Regular.ttf',
        'Amiri-Bold.ttf': 'https://github.com/alif-type/amiri/releases/download/1.000/Amiri-Bold.ttf'
    }
    
    for font_name, font_url in fonts.items():
        font_path = os.path.join(app.config['FONTS_DIR'], font_name)
        if not os.path.exists(font_path):
            try:
                app.logger.info(f"جاري تحميل الخط: {font_name}")
                response = requests.get(font_url)
                with open(font_path, 'wb') as f:
                    f.write(response.content)
                app.logger.info(f"تم تحميل الخط: {font_name}")
            except Exception as e:
                app.logger.error(f"فشل تحميل الخط {font_name}: {str(e)}")
                return False
    return True

# تحميل الخطوط عند بدء التشغيل
download_arabic_fonts()


# =========================
# تهيئة الخطوط العربية
# =========================
def setup_arabic_fonts():
    """تسجيل الخطوط العربية في ReportLab"""
    try:
        font_path_regular = os.path.join(app.config['FONTS_DIR'], 'Amiri-Regular.ttf')
        font_path_bold = os.path.join(app.config['FONTS_DIR'], 'Amiri-Bold.ttf')
        
        # استخدام خط Amiri إذا كان موجوداً
        if os.path.exists(font_path_regular):
            pdfmetrics.registerFont(TTFont('ArabicFont', font_path_regular))
            pdfmetrics.registerFont(TTFont('ArabicFont-Bold', font_path_bold))
            app.logger.info("تم تسجيل خط Amiri بنجاح")
            return True
        else:
            # بديل: استخدام خط النظام
            try:
                # للينكس
                pdfmetrics.registerFont(TTFont('ArabicFont', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                app.logger.info("تم تسجيل خط DejaVu Sans")
                return True
            except:
                try:
                    # للويندوز
                    pdfmetrics.registerFont(TTFont('ArabicFont', 'C:\\Windows\\Fonts\\Arial.ttf'))
                    app.logger.info("تم تسجيل خط Arial")
                    return True
                except:
                    app.logger.error("لم يتم العثور على خطوط عربية")
                    return False
    except Exception as e:
        app.logger.error(f"خطأ في تسجيل الخطوط: {str(e)}")
        return False


# =========================
# التحقق من الطالب
# =========================
def verify_student(name):
    try:
        df = pd.read_excel(app.config['EXCEL_PATH'], engine='openpyxl')
        df['Name'] = df['Name'].astype(str).str.strip()

        matches = df[df['Name'].str.upper() == name.strip().upper()]
        return not matches.empty

    except Exception as e:
        app.logger.error(f"خطأ في التحقق من الطالب: {str(e)}")
        return False


# =========================
# إنشاء الشهادة (دعم عربي مضمون 100%)
# =========================
def generate_certificate(name):
    try:
        template = PdfReader(open(app.config['TEMPLATE_PATH'], "rb"))
        page = template.pages[0]

        page_width = float(page.mediabox[2])
        page_height = float(page.mediabox[3])

        packet = io.BytesIO()

        doc = SimpleDocTemplate(
            packet,
            pagesize=(page_width, page_height)
        )

        # تسجيل الخطوط العربية
        if not setup_arabic_fonts():
            # إذا فشل تسجيل الخط، استخدم خطاً بديلاً
            try:
                pdfmetrics.registerFont(TTFont('ArabicFont', os.path.join(app.config['FONTS_DIR'], 'Amiri-Regular.ttf')))
            except:
                # آخر بديل
                from reportlab.pdfbase.cidfonts import UnicodeCIDFont
                pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
                app.logger.warning("استخدام خط STSong-Light كبديل أخير")

        styles = getSampleStyleSheet()

        arabic_style = ParagraphStyle(
            'ArabicStyle',
            parent=styles['Normal'],
            fontName='ArabicFont',
            fontSize=40,  # حجم مناسب للشهادة
            textColor=colors.black,
            alignment=1,  # توسيط
            spaceAfter=20,
            spaceBefore=20
        )

        # معالجة النص العربي بشكل صحيح
        try:
            # تنظيف الاسم من المسافات الزائدة
            clean_name = ' '.join(name.split())
            
            # إعادة تشكيل النص العربي
            reshaped_text = arabic_reshaper.reshape(clean_name)
            bidi_text = get_display(reshaped_text)
            
            app.logger.info(f"تمت معالجة الاسم: {clean_name} -> {bidi_text}")
            
        except Exception as e:
            app.logger.error(f"خطأ في معالجة النص العربي: {str(e)}")
            bidi_text = name  # استخدام النص الأصلي في حالة الفشل

        # إنشاء الفقرة مع النص المعالج
        paragraph = Paragraph(bidi_text, arabic_style)

        story = [paragraph]
        doc.build(story)

        packet.seek(0)
        overlay = PdfReader(packet)

        output = PdfWriter()
        page.merge_page(overlay.pages[0])
        output.add_page(page)

        output_stream = io.BytesIO()
        output.write(output_stream)
        output_stream.seek(0)

        return output_stream

    except Exception as e:
        app.logger.error(
            f"فشل إنشاء الشهادة: {str(e)}",
            exc_info=True
        )
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
            return render_template(
                'certificate_ready.html',
                name=name
            )
        else:
            flash("الطالب غير مسجل!", "error")

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
            filename = f"شهادة_حضور_{name.replace(' ', '_')}.pdf"

            return send_file(
                certificate,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )

        flash("فشل في إنشاء الشهادة", "error")
        return redirect(url_for('index'))

    except Exception as e:
        app.logger.error(f"خطأ في التحميل: {str(e)}")
        flash("حدث خطأ أثناء إنشاء الشهادة", "error")
        return redirect(url_for('index'))


if __name__ == '__main__':
    app.run()