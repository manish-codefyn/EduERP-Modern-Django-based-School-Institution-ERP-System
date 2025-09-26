🗄️ API Reference - EduERP
🌐 Base Information
API Endpoint
text
https://yourdomain.com/api/v1/
Authentication
EduERP API uses Token-based authentication. Include the token in the Authorization header:

http
Authorization: Token your_api_token_here
Response Format
All API responses follow this standardized format:

Success Response:

json
{
    "status": "success",
    "data": {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com"
    },
    "message": "Operation completed successfully",
    "timestamp": "2024-01-15T10:30:00Z",
    "pagination": {
        "count": 150,
        "next": "https://api.example.com/api/v1/students/?page=2",
        "previous": null,
        "page_size": 50
    }
}
Error Response:

json
{
    "status": "error",
    "error": {
        "code": "validation_error",
        "message": "Invalid input data",
        "details": {
            "email": ["This field is required."],
            "phone": ["Enter a valid phone number."]
        }
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
Common HTTP Status Codes
Code	Description
200	OK - Successful request
201	Created - Resource created successfully
400	Bad Request - Invalid input data
401	Unauthorized - Authentication required
403	Forbidden - Insufficient permissions
404	Not Found - Resource doesn't exist
429	Too Many Requests - Rate limit exceeded
500	Internal Server Error - Server-side issue
🔑 Authentication API
Login
http
POST /api/v1/auth/login/
Request Body:

json
{
    "username": "user@school.com",
    "password": "secure_password_123"
}
Response:

json
{
    "status": "success",
    "data": {
        "token": "abc123def456ghi789",
        "user": {
            "id": 1,
            "username": "user@school.com",
            "email": "user@school.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "teacher",
            "school": {
                "id": 1,
                "name": "Springfield High School",
                "code": "SHS"
            },
            "permissions": ["view_students", "edit_grades"]
        }
    },
    "message": "Login successful"
}
Token Refresh
http
POST /api/v1/auth/token/refresh/
Request Body:

json
{
    "token": "current_token_here"
}
Response:

json
{
    "status": "success",
    "data": {
        "token": "new_refreshed_token_here"
    },
    "message": "Token refreshed successfully"
}
Logout
http
POST /api/v1/auth/logout/
Headers:

http
Authorization: Token your_token_here
Response:

json
{
    "status": "success",
    "data": null,
    "message": "Logged out successfully"
}
Password Reset
http
POST /api/v1/auth/password/reset/
Request Body:

json
{
    "email": "user@school.com"
}
👥 User Management API
Get Current User
http
GET /api/v1/users/me/
Response:

json
{
    "status": "success",
    "data": {
        "id": 1,
        "username": "teacher@school.com",
        "email": "teacher@school.com",
        "first_name": "Sarah",
        "last_name": "Wilson",
        "role": "teacher",
        "is_active": true,
        "last_login": "2024-01-15T08:30:00Z",
        "date_joined": "2023-08-01T10:00:00Z",
        "profile": {
            "phone": "+1234567890",
            "address": "123 Main St, Springfield",
            "date_of_birth": "1985-05-15",
            "gender": "female"
        },
        "school": {
            "id": 1,
            "name": "Springfield High School",
            "code": "SHS"
        }
    },
    "message": "User data retrieved successfully"
}
List Users
http
GET /api/v1/users/
Query Parameters:

Parameter	Type	Description
role	string	Filter by role (teacher, student, parent, staff)
is_active	boolean	Filter by active status
search	string	Search in name, email, username
page	integer	Page number for pagination
page_size	integer	Number of items per page (default: 50)
Response:

json
{
    "status": "success",
    "data": {
        "count": 245,
        "next": "https://api.school.com/api/v1/users/?page=2",
        "previous": null,
        "results": [
            {
                "id": 1,
                "username": "teacher1@school.com",
                "first_name": "Sarah",
                "last_name": "Wilson",
                "email": "teacher1@school.com",
                "role": "teacher",
                "is_active": true,
                "last_login": "2024-01-15T08:30:00Z"
            },
            {
                "id": 2,
                "username": "student1@school.com",
                "first_name": "John",
                "last_name": "Doe",
                "email": "student1@school.com",
                "role": "student",
                "is_active": true,
                "last_login": "2024-01-14T15:45:00Z"
            }
        ]
    },
    "message": "Users retrieved successfully"
}
Create User
http
POST /api/v1/users/
Request Body:

json
{
    "username": "newuser@school.com",
    "email": "newuser@school.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "password": "secure_password_123",
    "role": "teacher",
    "profile": {
        "phone": "+1234567890",
        "date_of_birth": "1990-08-20",
        "gender": "female"
    }
}
Update User
http
PATCH /api/v1/users/{id}/
Request Body:

json
{
    "first_name": "Jane Updated",
    "profile": {
        "phone": "+1987654321"
    }
}
🎓 Student Management API
List Students
http
GET /api/v1/students/
Query Parameters:

Parameter	Type	Description
class_id	integer	Filter by class
section	string	Filter by section
is_active	boolean	Filter by active status
search	string	Search by name or admission number
page	integer	Page number
Response:

json
{
    "status": "success",
    "data": {
        "count": 150,
        "next": "https://api.school.com/api/v1/students/?page=2",
        "previous": null,
        "results": [
            {
                "id": 1,
                "admission_number": "S2024001",
                "first_name": "Alice",
                "last_name": "Johnson",
                "date_of_birth": "2008-05-15",
                "gender": "female",
                "admission_date": "2023-04-01",
                "is_active": true,
                "current_class": {
                    "id": 5,
                    "name": "Grade 10-A",
                    "section": "A"
                },
                "parent": {
                    "id": 101,
                    "name": "Mr. Johnson",
                    "email": "parent@example.com",
                    "phone": "+1234567890"
                }
            }
        ]
    },
    "message": "Students retrieved successfully"
}
Get Student Details
http
GET /api/v1/students/{id}/
Response:

json
{
    "status": "success",
    "data": {
        "id": 1,
        "admission_number": "S2024001",
        "first_name": "Alice",
        "last_name": "Johnson",
        "date_of_birth": "2008-05-15",
        "gender": "female",
        "blood_group": "O+",
        "religion": "Christian",
        "nationality": "American",
        "address": "123 Main Street, Springfield",
        "phone": "+1234567890",
        "email": "alice.johnson@student.school.com",
        "admission_date": "2023-04-01",
        "is_active": true,
        "current_class": {
            "id": 5,
            "name": "Grade 10-A",
            "section": "A"
        },
        "parent": {
            "id": 101,
            "name": "Robert Johnson",
            "email": "robert.johnson@email.com",
            "phone": "+1234567890",
            "occupation": "Engineer"
        },
        "medical_info": {
            "allergies": ["Peanuts", "Dust"],
            "medications": ["Inhaler"],
            "emergency_contact": {
                "name": "Mary Johnson",
                "relationship": "Mother",
                "phone": "+1987654321"
            }
        }
    },
    "message": "Student details retrieved successfully"
}
Create Student
http
POST /api/v1/students/
Request Body:

json
{
    "admission_number": "S2024150",
    "first_name": "Michael",
    "last_name": "Brown",
    "date_of_birth": "2009-03-20",
    "gender": "male",
    "admission_date": "2024-01-15",
    "class_id": 5,
    "section": "B",
    "parent": {
        "name": "David Brown",
        "email": "david.brown@email.com",
        "phone": "+1122334455",
        "occupation": "Doctor"
    },
    "address": "456 Oak Avenue, Springfield",
    "phone": "+1122334455"
}
Update Student
http
PATCH /api/v1/students/{id}/
Request Body:

json
{
    "address": "789 Pine Road, Springfield",
    "phone": "+9988776655",
    "medical_info": {
        "allergies": ["Peanuts"],
        "emergency_contact": {
            "phone": "+6677889900"
        }
    }
}
👩‍🏫 Teacher Management API
List Teachers
http
GET /api/v1/teachers/
Query Parameters:

Parameter	Type	Description
department	string	Filter by department
is_active	boolean	Filter by active status
search	string	Search by name or employee ID
Response:

json
{
    "status": "success",
    "data": {
        "count": 25,
        "results": [
            {
                "id": 1,
                "employee_id": "T2024001",
                "user": {
                    "id": 10,
                    "first_name": "Sarah",
                    "last_name": "Wilson",
                    "email": "sarah.wilson@school.com",
                    "phone": "+1234567890"
                },
                "department": "Science",
                "qualification": "M.Sc. Physics",
                "experience": "8 years",
                "subjects": [
                    {
                        "id": 1,
                        "name": "Physics",
                        "code": "PHY"
                    },
                    {
                        "id": 2,
                        "name": "Mathematics",
                        "code": "MATH"
                    }
                ],
                "classes": [
                    {
                        "id": 5,
                        "name": "Grade 10-A"
                    },
                    {
                        "id": 6,
                        "name": "Grade 10-B"
                    }
                ],
                "is_active": true,
                "joining_date": "2020-06-01"
            }
        ]
    },
    "message": "Teachers retrieved successfully"
}
Get Teacher Details
http
GET /api/v1/teachers/{id}/
Response:

json
{
    "status": "success",
    "data": {
        "id": 1,
        "employee_id": "T2024001",
        "user": {
            "id": 10,
            "first_name": "Sarah",
            "last_name": "Wilson",
            "email": "sarah.wilson@school.com",
            "phone": "+1234567890",
            "date_of_birth": "1985-08-15"
        },
        "department": "Science",
        "qualification": "M.Sc. Physics, B.Ed.",
        "experience": "8 years",
        "specialization": "Theoretical Physics",
        "subjects": [
            {
                "id": 1,
                "name": "Physics",
                "code": "PHY",
                "description": "Advanced Physics"
            }
        ],
        "classes": [
            {
                "id": 5,
                "name": "Grade 10-A",
                "section": "A"
            }
        ],
        "timetable": [
            {
                "day": "Monday",
                "period": 1,
                "subject": "Physics",
                "class": "Grade 10-A"
            }
        ],
        "is_active": true,
        "joining_date": "2020-06-01",
        "salary_grade": "TG-5",
        "bank_details": {
            "account_number": "XXXXXX1234",
            "bank_name": "City Bank",
            "ifsc_code": "CBIN0123456"
        }
    },
    "message": "Teacher details retrieved successfully"
}
📚 Academic Management API
Class Management
http
GET /api/v1/classes/
POST /api/v1/classes/
GET /api/v1/classes/{id}/
PUT /api/v1/classes/{id}/
DELETE /api/v1/classes/{id}/
Class Object:

json
{
    "id": 5,
    "name": "Grade 10-A",
    "section": "A",
    "capacity": 40,
    "class_teacher": {
        "id": 1,
        "name": "Sarah Wilson"
    },
    "academic_year": "2023-2024",
    "subjects": [
        {
            "id": 1,
            "name": "Mathematics",
            "code": "MATH",
            "teacher": "John Smith"
        }
    ],
    "student_count": 35,
    "is_active": true
}
Subject Management
http
GET /api/v1/subjects/
POST /api/v1/subjects/
Subject Object:

json
{
    "id": 1,
    "name": "Mathematics",
    "code": "MATH",
    "description": "Advanced Mathematics including Algebra and Calculus",
    "department": "Science",
    "credits": 4,
    "theory_hours": 3,
    "practical_hours": 2,
    "is_elective": false,
    "teachers": [
        {
            "id": 1,
            "name": "John Smith",
            "email": "john.smith@school.com"
        }
    ]
}
Timetable Management
http
GET /api/v1/timetable/?class_id=5
Response:

json
{
    "status": "success",
    "data": {
        "class": {
            "id": 5,
            "name": "Grade 10-A"
        },
        "academic_year": "2023-2024",
        "timetable": {
            "monday": [
                {
                    "period": 1,
                    "start_time": "08:00",
                    "end_time": "08:45",
                    "subject": {
                        "id": 1,
                        "name": "Mathematics",
                        "code": "MATH"
                    },
                    "teacher": {
                        "id": 1,
                        "name": "John Smith"
                    },
                    "room": "Room 101"
                }
            ],
            "tuesday": [
                // ... similar structure
            ]
        }
    },
    "message": "Timetable retrieved successfully"
}
✅ Attendance API
Mark Attendance
http
POST /api/v1/attendance/
Request Body:

json
{
    "class_id": 5,
    "date": "2024-01-15",
    "records": [
        {
            "student_id": 1,
            "status": "present",  // present, absent, late
            "remarks": "On time"
        },
        {
            "student_id": 2,
            "status": "absent",
            "remarks": "Sick leave"
        },
        {
            "student_id": 3,
            "status": "late",
            "remarks": "Arrived at 8:15 AM"
        }
    ]
}
Response:

json
{
    "status": "success",
    "data": {
        "date": "2024-01-15",
        "class": "Grade 10-A",
        "total_students": 35,
        "present": 32,
        "absent": 2,
        "late": 1,
        "attendance_percentage": 94.29
    },
    "message": "Attendance marked successfully"
}
Get Attendance Report
http
GET /api/v1/attendance/report/
Query Parameters:

Parameter	Type	Description
student_id	integer	Student ID (optional)
class_id	integer	Class ID (optional)
start_date	string	Start date (YYYY-MM-DD)
end_date	string	End date (YYYY-MM-DD)
month	integer	Month number (1-12)
year	integer	Year (e.g., 2024)
Response:

json
{
    "status": "success",
    "data": {
        "student": {
            "id": 1,
            "name": "Alice Johnson",
            "admission_number": "S2024001"
        },
        "class": {
            "id": 5,
            "name": "Grade 10-A"
        },
        "period": {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "month": "January 2024"
        },
        "summary": {
            "total_days": 22,
            "present": 20,
            "absent": 2,
            "late": 0,
            "attendance_percentage": 90.91
        },
        "daily_records": [
            {
                "date": "2024-01-15",
                "status": "present",
                "remarks": ""
            },
            {
                "date": "2024-01-16",
                "status": "absent",
                "remarks": "Sick leave"
            }
        ]
    },
    "message": "Attendance report generated successfully"
}
📊 Examination API
Exam Schedule
http
GET /api/v1/exams/?class_id=5
Response:

json
{
    "status": "success",
    "data": {
        "class": {
            "id": 5,
            "name": "Grade 10-A"
        },
        "exams": [
            {
                "id": 1,
                "name": "First Term Examination",
                "type": "term",  // term, half_yearly, yearly, unit_test
                "start_date": "2024-03-01",
                "end_date": "2024-03-15",
                "status": "scheduled",  // scheduled, ongoing, completed
                "subjects": [
                    {
                        "subject_id": 1,
                        "subject_name": "Mathematics",
                        "exam_date": "2024-03-01",
                        "max_marks": 100,
                        "pass_marks": 33
                    }
                ]
            }
        ]
    },
    "message": "Exam schedule retrieved successfully"
}
Enter Marks
http
POST /api/v1/exams/{exam_id}/marks/
Request Body:

json
{
    "subject_id": 1,
    "marks_data": [
        {
            "student_id": 1,
            "marks_obtained": 85,
            "remarks": "Excellent performance"
        },
        {
            "student_id": 2,
            "marks_obtained": 72,
            "remarks": "Good effort"
        },
        {
            "student_id": 3,
            "marks_obtained": 45,
            "remarks": "Needs improvement"
        }
    ]
}
Response:

json
{
    "status": "success",
    "data": {
        "exam_id": 1,
        "subject_id": 1,
        "subject_name": "Mathematics",
        "marks_entered": 35,
        "average_marks": 68.5,
        "highest_marks": 95,
        "lowest_marks": 45
    },
    "message": "Marks entered successfully"
}
Get Student Results
http
GET /api/v1/students/{student_id}/results/
Query Parameters:

Parameter	Type	Description
exam_type	string	Filter by exam type
academic_year	string	Academic year (e.g., 2023-2024)
Response:

json
{
    "status": "success",
    "data": {
        "student": {
            "id": 1,
            "name": "Alice Johnson",
            "admission_number": "S2024001",
            "class": "Grade 10-A"
        },
        "academic_year": "2023-2024",
        "results": [
            {
                "exam_id": 1,
                "exam_name": "First Term Examination",
                "exam_type": "term",
                "exam_date": "2024-03-01",
                "total_marks": 500,
                "obtained_marks": 425,
                "percentage": 85.0,
                "grade": "A",
                "rank": 5,
                "subjects": [
                    {
                        "subject_name": "Mathematics",
                        "max_marks": 100,
                        "obtained_marks": 85,
                        "grade": "A",
                        "remarks": "Excellent"
                    }
                ]
            }
        ],
        "overall_performance": {
            "total_exams": 3,
            "average_percentage": 82.5,
            "best_subject": "Mathematics",
            "improvement": "+5.2%"
        }
    },
    "message": "Student results retrieved successfully"
}
💰 Finance API
Fee Structure
http
GET /api/v1/fee/structures/?class_id=5
Response:

json
{
    "status": "success",
    "data": {
        "class": {
            "id": 5,
            "name": "Grade 10-A"
        },
        "academic_year": "2023-2024",
        "fee_components": [
            {
                "id": 1,
                "name": "Tuition Fee",
                "amount": 5000,
                "frequency": "monthly",  // monthly, quarterly, yearly, one_time
                "due_date": "2024-02-01"
            },
            {
                "id": 2,
                "name": "Transport Fee",
                "amount": 1500,
                "frequency": "monthly",
                "due_date": "2024-02-01"
            },
            {
                "id": 3,
                "name": "Annual Charges",
                "amount": 2000,
                "frequency": "yearly",
                "due_date": "2024-04-01"
            }
        ],
        "total_amount": 6500,
        "late_fee_rules": {
            "enabled": true,
            "grace_period_days": 7,
            "late_fee_amount": 100,
            "late_fee_percentage": 2.0
        }
    },
    "message": "Fee structure retrieved successfully"
}
Generate Fee Invoice
http
POST /api/v1/fee/invoices/
Request Body:

json
{
    "student_id": 1,
    "fee_components": [1, 2, 3],
    "due_date": "2024-02-01",
    "remarks": "Second term fees"
}
Response:

json
{
    "status": "success",
    "data": {
        "invoice_id": "INV202400001",
        "student": {
            "id": 1,
            "name": "Alice Johnson",
            "admission_number": "S2024001",
            "class": "Grade 10-A"
        },
        "issue_date": "2024-01-15",
        "due_date": "2024-02-01",
        "total_amount": 6500,
        "status": "pending",
        "fee_breakdown": [
            {
                "component": "Tuition Fee",
                "amount": 5000
            },
            {
                "component": "Transport Fee",
                "amount": 1500
            }
        ],
        "payment_link": "https://payments.school.com/inv/INV202400001"
    },
    "message": "Fee invoice generated successfully"
}
Process Payment
http
POST /api/v1/fee/payments/
Request Body:

json
{
    "invoice_id": "INV202400001",
    "amount": 6500,
    "payment_method": "online",  // online, cash, cheque, bank_transfer
    "transaction_id": "txn_123456789",
    "payment_date": "2024-01-20",
    "remarks": "Paid via Razorpay"
}
Response:

json
{
    "status": "success",
    "data": {
        "payment_id": "PAY202400001",
        "invoice_id": "INV202400001",
        "student": {
            "id": 1,
            "name": "Alice Johnson"
        },
        "amount_paid": 6500,
        "payment_method": "online",
        "transaction_id": "txn_123456789",
        "payment_date": "2024-01-20",
        "status": "completed",
        "receipt_number": "RCP202400001"
    },
    "message": "Payment processed successfully"
}
Payment Gateway Webhook
http
POST /api/v1/fee/payment-webhook/
Headers:

http
X-Razorpay-Signature: signature_here
Content-Type: application/json
Payload (Razorpay example):

json
{
    "event": "payment.captured",
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_123456789",
                "amount": 650000,  // in paise
                "currency": "INR",
                "status": "captured",
                "order_id": "order_123456",
                "invoice_id": "INV202400001",
                "method": "card",
                "created_at": 1674567890
            }
        }
    }
}
📖 Library API
Book Catalog
http
GET /api/v1/library/books/
Query Parameters:

Parameter	Type	Description
search	string	Search by title, author, ISBN
category	string	Filter by category
available	boolean	Show only available books
page	integer	Page number
Response:

json
{
    "status": "success",
    "data": {
        "count": 1250,
        "results": [
            {
                "id": 1,
                "isbn": "978-0123456789",
                "title": "Advanced Mathematics",
                "author": "John Smith",
                "publisher": "Educational Press",
                "publication_year": 2022,
                "category": "Mathematics",
                "total_copies": 5,
                "available_copies": 3,
                "location": "Shelf A-15",
                "description": "Comprehensive guide to advanced mathematics...",
                "tags": ["mathematics", "advanced", "calculus"]
            }
        ]
    },
    "message": "Books retrieved successfully"
}
Issue Book
http
POST /api/v1/library/transactions/
Request Body:

json
{
    "book_id": 1,
    "student_id": 1,
    "issue_date": "2024-01-15",
    "due_date": "2024-01-30",
    "remarks": "For mathematics project"
}
Response:

json
{
    "status": "success",
    "data": {
        "transaction_id": "LIB202400001",
        "book": {
            "id": 1,
            "title": "Advanced Mathematics",
            "author": "John Smith"
        },
        "student": {
            "id": 1,
            "name": "Alice Johnson",
            "admission_number": "S2024001"
        },
        "issue_date": "2024-01-15",
        "due_date": "2024-01-30",
        "status": "issued",
        "fine_amount": 0,
        "remarks": "For mathematics project"
    },
    "message": "Book issued successfully"
}
Return Book
http
POST /api/v1/library/transactions/{transaction_id}/return/
Request Body:

json
{
    "return_date": "2024-01-28",
    "condition": "good",  // good, damaged, lost
    "remarks": "Returned in good condition"
}
🔍 Search API
Global Search
http
GET /api/v1/search/?q=search_term
Query Parameters:

Parameter	Type	Description
q	string	Search term (required)
type	string	Filter by type (students, teachers, books)
limit	integer	Limit results per category
Response:

json
{
    "status": "success",
    "data": {
        "query": "alice",
        "total_results": 15,
        "results": {
            "students": [
                {
                    "id": 1,
                    "name": "Alice Johnson",
                    "admission_number": "S2024001",
                    "class": "Grade 10-A",
                    "type": "student"
                }
            ],
            "teachers": [
                {
                    "id": 5,
                    "name": "Alice Brown",
                    "employee_id": "T2024005",
                    "department": "English",
                    "type": "teacher"
                }
            ],
            "books": [
                {
                    "id": 12,
                    "title": "Alice in Wonderland",
                    "author": "Lewis Carroll",
                    "category": "Fiction",
                    "type": "book"
                }
            ]
        }
    },
    "message": "Search completed successfully"
}
📊 Reports API
Generate Report
http
POST /api/v1/reports/generate/
Request Body:

json
{
    "report_type": "attendance_summary",
    "parameters": {
        "class_id": 5,
        "month": 1,
        "year": 2024
    },
    "format": "pdf",  // pdf, excel, json, html
    "include_charts": true
}
Response:

json
{
    "status": "success",
    "data": {
        "report_id": "REP202400001",
        "report_type": "attendance_summary",
        "status": "generating",
        "download_url": "https://api.school.com/api/v1/reports/REP202400001/download/",
        "estimated_time": 30
    },
    "message": "Report generation started"
}
Download Report
http
GET /api/v1/reports/{report_id}/download/
📢 Notifications API
Get Notifications
http
GET /api/v1/notifications/
Query Parameters:

Parameter	Type	Description
unread_only	boolean	Show only unread notifications
type	string	Filter by notification type
limit	integer	Number of notifications to return
Response:

json
{
    "status": "success",
    "data": {
        "unread_count": 5,
        "notifications": [
            {
                "id": 1,
                "title": "Fee Payment Reminder",
                "message": "Fee payment due for January 2024",
                "type": "fee_reminder",
                "is_read": false,
                "created_at": "2024-01-10T09:00:00Z",
                "action_url": "/fee/payment/INV202400001",
                "metadata": {
                    "invoice_id": "INV202400001",
                    "due_date": "2024-01-15"
                }
            },
            {
                "id": 2,
                "title": "Exam Schedule Published",
                "message": "First term exam schedule is now available",
                "type": "exam_notification",
                "is_read": true,
                "created_at": "2024-01-05T14:30:00Z",
                "action_url": "/exams/schedule/1"
            }
        ]
    },
    "message": "Notifications retrieved successfully"
}
Mark Notification as Read
http
POST /api/v1/notifications/{notification_id}/mark-read/
⚡ Rate Limiting
API endpoints are rate-limited to prevent abuse:

Endpoint Category	Limit	Window
Authentication	5 requests	1 minute
Read operations	100 requests	1 minute
Write operations	30 requests	1 minute
File uploads	10 requests	1 minute
Rate Limit Headers in Response:

http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 164215