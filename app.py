#app.py
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
import io
import os
import logging
import pandas as pd
import sys

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-123')

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    app.config['TEMPLATE_PATH'] = os.path.join(BASE_DIR, 'static', 'certificates', 'template.pdf')
    app.config['EXCEL_PATH'] = os.path.join(BASE_DIR, 'students.xlsx')

    app.logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    app.logger.addHandler(stream_handler)

    return app

app = create_app()

def verify_student(name, national_id):
    try:
        df = pd.read_excel(app.config['EXCEL_PATH'], engine='openpyxl')
        df['Name'] = df['Name'].astype(str).str.strip()
        df['NationalID'] = df['NationalID'].astype(str).str.strip()

        matches = df[
            (df['Name'].str.upper() == name.strip().upper()) &
            (df['NationalID'] == str(national_id).strip())
        ]
        return not matches.empty
    except Exception as e:
        app.logger.error(f"خطأ في التحقق من الطالب: {str(e)}")
        return False

def generate_certificate(name):
    """إنشاء شهادة مع ضبط دقيق لموقع الاسم"""
    try:
        # 1. قراءة ملف القالب
        template = PdfReader(open(app.config['TEMPLATE_PATH'], "rb"))
        if len(template.pages) == 0:
            raise ValueError("ملف القالب فارغ أو تالف")
        
        # 2. الحصول على أبعاد الصفحة
        page = template.pages[0]
        page_width = float(page.mediabox[2])
        page_height = float(page.mediabox[3])
        
        # 3. إنشاء طبقة الاسم
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))
        
        # 4. إعداد الخط
        font_name = "Helvetica-Bold"
        font_size = 25
        
        # 5. الإحداثيات المطلوبة (ضبط هذه القيم حسب حاجتك)
        x_pos = 170  # المسافة من الحافة اليسرى
        y_pos = 315 # المسافة من الحافة السفلية
        
        # 6. حساب الإحداثيات الحقيقية (PDF يستخدم نظام إحداثيات من الأسفل)
        real_y = page_height - y_pos
        
        # 7. رسم خلفية بيضاء لتغطية النص القديم
        
        # 8. كتابة الاسم الجديد
        can.setFillColorRGB(0, 0, 0)  # أسود
        can.setFont(font_name, font_size)
        can.drawString(x_pos, real_y, name)
        can.save()
        
        # 9. دمج مع القالب
        packet.seek(0)
        overlay = PdfReader(packet)
        
        output = PdfWriter()
        page.merge_page(overlay.pages[0])
        output.add_page(page)
        
        # 10. إرجاع النتيجة
        output_stream = io.BytesIO()
        output.write(output_stream)
        output_stream.seek(0)
        
        return output_stream

    except Exception as e:
        app.logger.error(f"فشل إنشاء الشهادة: {str(e)}", exc_info=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        national_id = request.form.get('national_id', '').strip()

        if not name or not national_id:
            flash("يجب إدخال اسم الطالب والرقم القومي", "error")
            return redirect(url_for('index'))

        if verify_student(name, national_id):
            return render_template('certificate_ready.html', name=name)
        else:
            flash("الطالب غير مسجل! يرجى التأكد من البيانات", "error")

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
