#excel.py
import pandas as pd
import os

def check_student(name, national_id):
    try:
        excel_path = os.path.join(os.path.dirname(__file__), 'students.xlsx')
        if not os.path.exists(excel_path):
            return {
                "status": "error",
                "message": "ملف الطلاب غير موجود"
            }
            
        df = pd.read_excel(excel_path)
        
        required_columns = ['Name', 'NationalID', 'Grade']
        if not all(col in df.columns for col in required_columns):
            return {
                "status": "error",
                "message": "هيكل ملف الطلاب غير صحيح"
            }
            
        result = df[(df['Name'].str.strip().str.lower() == name.strip().lower()) & 
                   (df['NationalID'].astype(str) == str(national_id))]
        
        if not result.empty:
            student = result.iloc[0]
            return {
                "status": "accepted",
                "name": student['Name'],
                "grade": student['Grade']
            }
        else:
            return {
                "status": "rejected",
                "message": "الطالب غير مسجل"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"حدث خطأ: {str(e)}"
        }