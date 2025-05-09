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

# المسارات النسبية الآمنة
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, 'static', 'certificates', 'template.pdf')
EXCEL_PATH = os.path.join(BASE_DIR, 'students.xlsx')

def verify_student(name, national_id):
    try:
        df = pd.read_excel(EXCEL_PATH, engine='openpyxl')
        df['Name'] = df['Name'].astype(str).str.strip()
        df['NationalID'] = df['NationalID'].astype(str).str.strip()
        
        matches = df[
            (df['Name'].str.upper() == name.strip().upper()) & 
            (df['NationalID'] == str(national_id).strip())
        ]
        return not matches.empty
    except Exception as e:
        app.logger.error(f"Error verifying student: {str(e)}")
        return False

def generate_certificate(name):
    try:
        template = PdfReader(open(TEMPLATE_PATH, "rb"))
        page = template.pages[0]
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        
        # إعداد النص (اضبط القيم حسب تصميمك)
        text_width = can.stringWidth(name, "Helvetica-Bold", 50)
        can.setFont("Helvetica-Bold", 50)
        can.drawString((letter[0]-text_width)/2, 350, name)
        can.save()
        
        # دمج PDF
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
        app.logger.error(f"Certificate generation failed: {str(e)}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        national_id = request.form.get('national_id', '').strip()
        
        if not name or not national_id:
            flash("All fields are required", "error")
            return redirect(url_for('index'))
            
        if verify_student(name, national_id):
            return render_template('certificate_ready.html', name=name)
        else:
            flash("Student not found. Please check your details.", "error")
    
    return render_template('form.html')

@app.route('/download', methods=['POST'])
def download_certificate():
    try:
        name = request.form.get('name', '').strip()
        if not name:
            flash("Name is required", "error")
            return redirect(url_for('index'))
            
        certificate = generate_certificate(name)
        if certificate:
            return send_file(
                certificate,
                as_attachment=True,
                download_name=f"Certificate_{name.replace(' ', '_')}.pdf",
                mimetype='application/pdf'
            )
        flash("Certificate generation failed", "error")
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Download error: {str(e)}")
        flash("An error occurred", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    # إعداد السجلات
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    app.run(host='0.0.0.0', port=5000, debug=True)