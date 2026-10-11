"""Hợp đồng schema của file nguồn academic_survival_longitudinal.csv (22 cột, đúng thứ tự).

Kiểu cột:
  id       – mã định danh (chuỗi)
  int      – số nguyên
  float    – số thực
  binary   – 0/1
  category – chuỗi phân loại
"""

COLUMNS = {
    "Student_ID": "id",
    "Age": "int",
    "Gender": "category",
    "First_Generation": "binary",
    "Family_Income": "float",
    "Household_Size": "int",
    "Housing_Status": "category",
    "Scholarship": "binary",
    "Tuition_Base": "float",
    "Semester": "int",
    "Course_Load": "int",
    "Work_Hours": "float",
    "Emergency_Expense": "float",
    "Sem_GPA": "float",
    "Attendance": "float",
    "LMS_Logins": "int",
    "Advising_Visits": "int",
    "Failed_Courses": "int",
    "Financial_Stress": "float",
    "Target_Dropout_Next_Sem": "binary",
    "End_of_Semester_Status": "category",
    "Censored": "binary",
}

NUMERIC_KINDS = {"int", "float", "binary"}
