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

# Thuộc tính không đổi qua các kỳ của cùng một sinh viên (đã kiểm tra trên dữ liệu gốc)
STATIC_COLUMNS = [
    "Age", "Gender", "First_Generation", "Family_Income",
    "Household_Size", "Housing_Status", "Scholarship", "Tuition_Base",
]

# Cách ghi Gender trong dữ liệu thô (sau strip().lower()) → nhóm chuẩn. Giá trị ngoài bảng là lỗi.
GENDER_MAP = {
    "female": "Female",
    "f": "Female",
    "male": "Male",
    "m": "Male",
    "other": "Other/Unknown",
    "prefer not to say": "Other/Unknown",
}

HOUSING_VALUES = {"On-Campus", "Off-Campus", "With Parents"}
STATUS_VALUES = {"Enrolled", "Dropped_Out", "Graduated"}

# Miền giá trị hợp lệ (min, max); None = không giới hạn phía đó
RANGES = {
    "Age": (15, 60),
    "Family_Income": (1, None),
    "Household_Size": (1, 15),
    "Tuition_Base": (1, None),
    "Semester": (1, 8),
    "Course_Load": (1, 30),
    "Work_Hours": (0, 80),
    "Emergency_Expense": (0, None),
    "Sem_GPA": (0, 4),
    "Attendance": (0, 100),
    "LMS_Logins": (0, None),
    "Advising_Visits": (0, None),
    "Failed_Courses": (0, None),
    "Financial_Stress": (1, None),
}
