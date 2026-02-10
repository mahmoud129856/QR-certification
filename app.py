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

def verify_student(name):
    """التحقق من الطالب بالاسم فقط"""
    try:
        df = pd.read_excel(app.config['EXCEL_PATH'], engine='openpyxl')
        df['Name'] = df['Name'].astype(str).str.strip()

        matches = df[
            df['Name'].str.upper() == name.strip().upper()
        ]
        return not matches.empty
    except Exception as e:
        app.logger.error(f"خطأ في التحقق من الطالب: {str(e)}")
        return False

def generate_certificate(name):
    """إنشاء شهادة مع ضبط دقيق لموقع الاسم"""
    try:
        template = PdfReader(open(app.config['TEMPLATE_PATH'], "rb"))
        if len(template.pages) == 0:
            raise ValueError("ملف القالب فارغ أو تالف")

        page = template.pages[0]
        page_width = float(page.mediabox[2])
        page_height = float(page.mediabox[3])

        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))

        font_name = "Helvetica-Bold"
        font_size = 25

        x_pos = 170
        y_pos = 315
        real_y = page_height - y_pos

        can.setFillColorRGB(0, 0, 0)
        can.setFont(font_name, font_size)
        can.drawString(x_pos, real_y, name)
        can.save()

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
        app.logger.error(f"فشل إنشاء الشهادة: {str(e)}", exc_info=True)
        return None

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