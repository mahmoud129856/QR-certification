from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import pandas as pd
import io
from weasyprint import HTML

app = Flask(__name__)
app.secret_key = 'dev-key-123'

# مسار ملف Excel للطلاب
EXCEL_PATH = 'students.xlsx'


# =========================
# التحقق من الطالب
# =========================
def verify_student(name):
    try:
        df = pd.read_excel(EXCEL_PATH, engine='openpyxl')
        df['Name'] = df['Name'].astype(str).str.strip()
        matches = df[df['Name'].str.upper() == name.strip().upper()]
        return not matches.empty
    except Exception as e:
        print(f"خطأ في التحقق من الطالب: {e}")
        return False


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
            flash("الطالب غير مسجل!", "error")
    return render_template('form.html')


# =========================
# تحميل الشهادة PDF
# =========================
@app.route('/download', methods=['POST'])
def download_certificate():
    try:
        name = request.form.get('name', '').strip()
        if not name:
            flash("اسم الطالب مطلوب", "error")
            return redirect(url_for('index'))

        # توليد HTML للشهادة مع الاسم
        html_content = render_template('certificate_template.html', name=name)

        pdf_file = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_file)
        pdf_file.seek(0)

        filename = f"شهادة_حضور_{name.replace(' ', '_')}.pdf"
        return send_file(
            pdf_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f"خطأ أثناء إنشاء الشهادة: {e}")
        flash("حدث خطأ أثناء إنشاء الشهادة", "error")
        return redirect(url_for('index'))


if __name__ == '__main__':
    app.run()