from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
import os
import logging
import pandas as pd
import sys

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-123')

    # المسارات
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    app.config['TEMPLATE_PATH'] = os.path.join(BASE_DIR, 'static', 'certificates', 'template.pdf')
    app.config['EXCEL_PATH'] = os.path.join(BASE_DIR, 'students.xlsx')

    # إعداد اللوجينج ليشتغل مع Vercel (بدون الكتابة على ملفات)
    app.logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    app.logger.addHandler(handler)

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
    try:
        template = PdfReader(open(app.config['TEMPLATE_PATH'], "rb"))
        page = template.pages[0]
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)

        font_name = "Helvetica"  # تأكد إنه مدعوم
        font_size = 50

        text_width = can.stringWidth(name, font_name, font_size)
        can.setFont(font_name, font_size)
        can.drawString((letter[0]-text_width)/2, 350, name)
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
        app.logger.error(f"فشل في إنشاء الشهادة: {str(e)}")
        return None

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
