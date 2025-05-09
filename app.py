from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
import os
import logging
import pandas as pd
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# المسارات المهمة
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'static', 'certificates', 'template.pdf')
EXCEL_PATH = "D:/APP/students.xlsx"

def verify_student(name, national_id):
    try:
        df = pd.read_excel(EXCEL_PATH)
        
        # تنظيف البيانات
        df = df.dropna(how='all')  # حذف الصفوف الفارغة
        df['Name'] = df['Name'].astype(str).str.strip()
        df['NationalID'] = df['NationalID'].astype(str).str.strip()
        
        # البحث مع تسجيل النتائج
        matches = df[
            (df['Name'].str.upper() == name.strip().upper()) &
            (df['NationalID'] == str(national_id).strip())
        ]
        
        if not matches.empty:
            app.logger.info(f"تم العثور على الطالب:\n{matches.iloc[0]}")
            return True
            
        app.logger.warning("لم يتم العثور على طالب مطابق")
        app.logger.info(f"أقرب 5 نتائج:\n{df[df['Name'].str.contains(name.strip(), case=False)].head()}")
        return False
        
    except Exception as e:
        app.logger.error(f"خطأ في البحث: {str(e)}", exc_info=True)
        return False

def generate_certificate(name):
    """إنشاء شهادة PDF"""
    try:
        template = PdfReader(open(TEMPLATE_PATH, "rb"))
        if len(template.pages) == 0:
            raise ValueError("ملف القالب فارغ أو تالف")
        
        page = template.pages[0]
        page_width = float(page.mediabox[2])
        page_height = float(page.mediabox[3])
        
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))
        
        text_width = can.stringWidth(name, "Helvetica-Bold", 75)
        x_pos = (page_width - text_width) / 2
        y_pos = page_height * 0.625
        
        can.setFillColorRGB(1, 1, 1)
        can.rect(x_pos-10, y_pos-10, text_width+120, 78, fill=1, stroke=0)
        
        can.setFillColorRGB(0, 0, 0)
        can.setFont("Helvetica-Bold", 75)
        can.drawString(x_pos, y_pos, name)
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
        app.logger.error(f"فشل إنشاء الشهادة: {str(e)}")
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
            flash("Student not registered! Verify the data", "error")
        
        return redirect(url_for('index'))
    
    return render_template('form.html')

@app.route('/download', methods=['POST'])
def download_certificate():
    try:
        name = request.form.get('name', '').strip()
        if not name:
            flash("اسم الطالب مطلوب", "error")
            return redirect(url_for('index'))
            
        certificate = generate_certificate(name)
        if not certificate:
            flash("فشل في إنشاء الشهادة", "error")
            return redirect(url_for('index'))
            
        filename = f"شهادة_حضور_{name.replace(' ', '_')}.pdf"
        return send_file(
            certificate,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        app.logger.error(f"خطأ في التحميل: {str(e)}")
        flash("حدث خطأ أثناء إنشاء الشهادة", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    app.run(debug=True)