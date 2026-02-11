from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import io
import os
import logging
import pandas as pd
import sys


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

    app.logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    app.logger.addHandler(stream_handler)

    return app


app = create_app()


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
# إنشاء الشهادة - طريقة مباشرة باستخدام canvas
# =========================
def generate_certificate(name):
    try:
        # قراءة ملف القالب
        template = PdfReader(open(app.config['TEMPLATE_PATH'], "rb"))
        page = template.pages[0]
        
        # الحصول على أبعاد الصفحة
        page_width = float(page.mediabox[2])
        page_height = float(page.mediabox[3])
        
        # إنشاء overlay PDF
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))
        
        # محاولة استخدام خط يدعم العربية
        try:
            # محاولة استخدام Arial (موجود في معظم الأنظمة)
            pdfmetrics.registerFont(TTFont('Arabic', 'C:\\Windows\\Fonts\\Arial.ttf'))
        except:
            try:
                # للينكس
                pdfmetrics.registerFont(TTFont('Arabic', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            except:
                try:
                    # لماك
                    pdfmetrics.registerFont(TTFont('Arabic', '/System/Library/Fonts/Arial.ttf'))
                except:
                    # آخر بديل
                    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
                    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        
        # معالجة الاسم العربي
        try:
            reshaped_text = arabic_reshaper.reshape(name)
            bidi_text = get_display(reshaped_text)
        except:
            bidi_text = name
        
        # ضبط خصائص النص
        c.setFont('Arabic', 36)
        c.setFillColorRGB(0, 0, 0)  # لون أسود
        
        # تحديد موقع الاسم على الشهادة
        # هذه هي النقطة الأهم - جرب القيم التالية:
        
        # الخيار 1: في منتصف الشهادة
        x_position = page_width / 2
        y_position = page_height / 2 + 50  # عدل هذه القيمة حسب قالبك
        
        # رسم الاسم في المنتصف
        c.drawCentredString(x_position, y_position, bidi_text)
        
        c.save()
        
        # دمج الـ overlay مع القالب
        packet.seek(0)
        overlay = PdfReader(packet)
        
        # دمج الصفحات
        output = PdfWriter()
        page.merge_page(overlay.pages[0])
        output.add_page(page)
        
        # حفظ النتيجة
        output_stream = io.BytesIO()
        output.write(output_stream)
        output_stream.seek(0)
        
        app.logger.info(f"تم إنشاء شهادة لـ: {name} في الموقع: ({x_position}, {y_position})")
        
        return output_stream
        
    except Exception as e:
        app.logger.error(f"فشل إنشاء الشهادة: {str(e)}", exc_info=True)
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