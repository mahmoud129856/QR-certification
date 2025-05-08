#app.py
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from fpdf import FPDF
from io import BytesIO
import pandas as pd
import os
from datetime import datetime
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# مسارات الملفات
FONT_PATH = os.path.join('static', 'fonts', 'Amiri-Regular.ttf')
EXCEL_PATH = os.path.join('students.xlsx')

def generate_certificate(name, grade):
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        # استخدام الخط العربي إذا موجود
        if os.path.exists(FONT_PATH):
            pdf.add_font('Arabic', '', FONT_PATH, uni=True)
            pdf.set_font('Arabic', '', 16)
            
            def format_arabic(text):
                try:
                    return get_display(reshape(str(text)))
                except:
                    return str(text)
            
            pdf.cell(0, 10, txt=format_arabic("شهادة تقدير"), ln=True, align='C')
            pdf.cell(0, 10, txt=format_arabic(f"الطالب/ة: {name}"), ln=True, align='C')
            pdf.cell(0, 10, txt=format_arabic(f"التقدير: {grade}"), ln=True, align='C')
            pdf.cell(0, 10, txt=format_arabic(f"تاريخ الإصدار: {datetime.now().strftime('%Y-%m-%d')}"), ln=True, align='C')
        else:
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, txt="Certificate of Achievement", ln=True, align='C')
            pdf.cell(0, 10, txt=f"Student: {name}", ln=True, align='C')
            pdf.cell(0, 10, txt=f"Grade: {grade}", ln=True, align='C')
            pdf.cell(0, 10, txt=f"Issued on: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align='C')

        # حفظ مؤقت للشهادة
        temp_path = 'temp_cert.pdf'
        pdf.output(temp_path)
        with open(temp_path, 'rb') as f:
            file_data = BytesIO(f.read())
        os.remove(temp_path)
        
        file_data.seek(0)
        return file_data
        
    except Exception as e:
        app.logger.error(f"Failed to generate certificate: {str(e)}", exc_info=True)
        return None

def validate_student(name, national_id):
    try:
        if not os.path.exists(EXCEL_PATH):
            flash("ملف الطلاب غير موجود", "error")
            return None
            
        df = pd.read_excel(EXCEL_PATH)
        
        # التحقق من الأعمدة المطلوبة
        required_columns = ['Name', 'NationalID', 'Grade']
        if not all(col in df.columns for col in required_columns):
            flash("هيكل ملف الطلاب غير صحيح", "error")
            return None
            
        # البحث الدقيق عن الطالب
        student = df[
            (df['Name'].str.strip().str.lower() == name.strip().lower()) & 
            (df['NationalID'].astype(str).str.strip() == str(national_id).strip())
        ]
        
        if not student.empty:
            return {
                'name': student.iloc[0]['Name'],
                'grade': student.iloc[0]['Grade']
            }
        return None
        
    except Exception as e:
        app.logger.error(f"Error validating student: {str(e)}", exc_info=True)
        flash("حدث خطأ أثناء التحقق من بيانات الطالب", "error")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        national_id = request.form.get('national_id', '').strip()
        
        if not name or not national_id:
            flash("الرجاء إدخال جميع البيانات المطلوبة", "error")
            return redirect(url_for('index'))
            
        if not national_id.isdigit():
            flash("الرقم القومي يجب أن يحتوي على أرقام فقط", "error")
            return redirect(url_for('index'))
            
        student_data = validate_student(name, national_id)
        if not student_data:
            flash("الطالب غير مسجل أو البيانات غير صحيحة", "error")
            return redirect(url_for('index'))
            
        return render_template('result.html', 
                            name=student_data['name'],
                            grade=student_data['grade'])
    
    return render_template('form.html')

@app.route('/download', methods=['POST'])
def download_certificate():
    try:
        name = request.form.get('name', '').strip()
        grade = request.form.get('grade', '').strip()
        
        if not name or not grade:
            flash("بيانات غير كافية لإنشاء الشهادة", "error")
            return redirect(url_for('index'))
            
        certificate = generate_certificate(name, grade)
        if not certificate:
            flash("فشل في إنشاء الشهادة", "error")
            return redirect(url_for('index'))
            
        filename = f"شهادة_{name.replace(' ', '_')}.pdf"
        return send_file(
            certificate,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        app.logger.error(f"Download error: {str(e)}", exc_info=True)
        flash("حدث خطأ أثناء تحميل الشهادة", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.ERROR)
    app.logger.addHandler(file_handler)
    
    app.run(debug=True, host='0.0.0.0', port=5000)