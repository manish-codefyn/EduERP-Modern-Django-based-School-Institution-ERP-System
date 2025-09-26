🧪 Testing Guide - EduERP
🏗️ Testing Strategy Overview
EduERP employs a comprehensive testing strategy to ensure code quality, reliability, and security across all modules.

Testing Pyramid
      ↗ UI Tests (5%)
     ↗ Integration Tests (15%)
    ↗ Unit Tests (80%)
Test Types Coverage
Unit Tests: 80% - Individual components

Integration Tests: 15% - Component interactions

API Tests: 10% - REST API endpoints

UI Tests: 5% - User interface (Selenium)

Performance Tests: Critical paths only

Security Tests: Authentication & authorization

🚀 Test Environment Setup
Prerequisites

# Install testing dependencies
pip install -r requirements/test.txt

# Setup test database
createdb eduerp_test

# Install test tools
pip install pytest pytest-django pytest-cov factory-boy
pip install selenium beautifulsoup4 faker
Environment Configuration
python
# config/settings/test.py
import os
from .base import *

# Test-specific settings
DEBUG = False
TESTING = True

# Use separate test database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'eduerp_test',
        'USER': os.getenv('TEST_DB_USER', 'postgres'),
        'PASSWORD': os.getenv('TEST_DB_PASSWORD', ''),
        'HOST': os.getenv('TEST_DB_HOST', 'localhost'),
        'PORT': os.getenv('TEST_DB_PORT', '5432'),
        'TEST': {
            'NAME': 'eduerp_test',
            'MIRROR': None,
        }
    }
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable caching in tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Test email backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable external APIs
PAYMENT_GATEWAYS = {
    'razorpay': {
        'enabled': False,
        'test_mode': True,
    }
}
🧩 Unit Testing
Test Structure Convention

apps/
├── students/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_views.py
│   │   ├── test_forms.py
│   │   ├── test_serializers.py
│   │   └── factories.py
Model Testing

# apps/students/tests/test_models.py
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.students.models import Student
from apps.organization.models import School
from .factories import StudentFactory, SchoolFactory

class TestStudentModel:
    """Test cases for Student model"""
    
    def test_student_creation(self):
        """Test student creation with valid data"""
        student = StudentFactory()
        assert student.admission_number is not None
        assert student.is_active is True
        assert str(student) == f"{student.first_name} {student.last_name} ({student.admission_number})"
    
    def test_unique_admission_number_per_school(self):
        """Test admission number uniqueness within school"""
        school = SchoolFactory()
        student1 = StudentFactory(school=school, admission_number="S1001")
        
        with pytest.raises(IntegrityError):
            StudentFactory(school=school, admission_number="S1001")
    
    def test_valid_date_of_birth(self):
        """Test date of birth validation"""
        student = StudentFactory()
        
        # Test future date validation
        with pytest.raises(ValidationError):
            student.date_of_birth = timezone.now().date() + timedelta(days=1)
            student.full_clean()
    
    def test_age_calculation(self):
        """Test age calculation method"""
        from datetime import date
        student = StudentFactory(date_of_birth=date(2010, 5, 15))
        
        with freeze_time("2024-01-15"):
            assert student.calculate_age() == 13
    
    def test_student_soft_delete(self):
        """Test soft delete functionality"""
        student = StudentFactory()
        student_id = student.id
        
        student.soft_delete()
        student.refresh_from_db()
        
        assert student.is_active is False
        assert Student.all_objects.get(id=student_id) is not None
        assert Student.objects.filter(id=student_id).exists() is False
View Testing

# apps/students/tests/test_views.py
import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from apps.students.models import Student
from .factories import StudentFactory, UserFactory

class TestStudentViews(APITestCase):
    """Test cases for Student views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.teacher_user = UserFactory(role='teacher')
        self.admin_user = UserFactory(role='admin')
        self.student = StudentFactory()
        
        # Authenticate as teacher
        self.client.force_authenticate(user=self.teacher_user)
    
    def test_student_list_view(self):
        """Test student list API"""
        url = reverse('student-list')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert response.data['count'] >= 1
    
    def test_student_create_view(self):
        """Test student creation API"""
        url = reverse('student-list')
        data = {
            'admission_number': 'S2024100',
            'first_name': 'Test',
            'last_name': 'Student',
            'date_of_birth': '2010-05-15',
            'gender': 'male',
            'class_id': self.student.current_class.id
        }
        
        # Only admin can create students
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Student.objects.filter(admission_number='S2024100').exists()
    
    def test_student_detail_view(self):
        """Test student detail API"""
        url = reverse('student-detail', kwargs={'pk': self.student.id})
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['admission_number'] == self.student.admission_number
    
    def test_unauthorized_access(self):
        """Test unauthorized access to student data"""
        unauthorized_user = UserFactory(role='student')
        self.client.force_authenticate(user=unauthorized_user)
        
        url = reverse('student-detail', kwargs={'pk': self.student.id})
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
Form Testing

# apps/students/tests/test_forms.py
from django.test import TestCase
from apps.students.forms import StudentForm, StudentSearchForm
from .factories import StudentFactory, ClassFactory

class TestStudentForms(TestCase):
    """Test cases for Student forms"""
    
    def test_student_form_valid_data(self):
        """Test student form with valid data"""
        class_obj = ClassFactory()
        form_data = {
            'admission_number': 'S2024101',
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '2010-05-15',
            'gender': 'male',
            'class_id': class_obj.id,
            'admission_date': '2024-01-15'
        }
        
        form = StudentForm(data=form_data)
        assert form.is_valid() is True
    
    def test_student_form_invalid_data(self):
        """Test student form with invalid data"""
        form_data = {
            'admission_number': '',  # Required field
            'first_name': 'A' * 51,  # Too long
            'date_of_birth': 'invalid-date',
        }
        
        form = StudentForm(data=form_data)
        assert form.is_valid() is False
        assert 'admission_number' in form.errors
        assert 'first_name' in form.errors
        assert 'date_of_birth' in form.errors
    
    def test_student_search_form(self):
        """Test student search form"""
        form_data = {
            'search_query': 'John Doe',
            'class_filter': '1',
            'is_active': True
        }
        
        form = StudentSearchForm(data=form_data)
        assert form.is_valid() is True
🔗 Integration Testing
API Integration Tests

# apps/api/tests/test_integration.py
import pytest
from django.urls import reverse
from rest_framework.test import APITestCase
from apps.students.models import Student, Attendance
from .factories import StudentFactory, AttendanceFactory, UserFactory

class TestStudentAttendanceIntegration(APITestCase):
    """Integration tests for student attendance workflow"""
    
    def setUp(self):
        self.teacher = UserFactory(role='teacher')
        self.student = StudentFactory()
        self.client.force_authenticate(user=self.teacher)
    
    def test_complete_attendance_workflow(self):
        """Test complete attendance marking workflow"""
        # Step 1: Mark attendance
        attendance_url = reverse('attendance-list')
        attendance_data = {
            'class_id': self.student.current_class.id,
            'date': '2024-01-15',
            'records': [
                {
                    'student_id': self.student.id,
                    'status': 'present',
                    'remarks': 'On time'
                }
            ]
        }
        
        response = self.client.post(attendance_url, attendance_data, format='json')
        assert response.status_code == 201
        
        # Step 2: Verify attendance recorded
        attendance = Attendance.objects.get(student=self.student, date='2024-01-15')
        assert attendance.status == 'present'
        
        # Step 3: Generate attendance report
        report_url = reverse('attendance-report')
        report_params = {
            'student_id': self.student.id,
            'month': 1,
            'year': 2024
        }
        
        response = self.client.get(report_url, report_params)
        assert response.status_code == 200
        assert response.data['summary']['present'] >= 1
Database Integration Tests

# tests/integration/test_database.py
from django.test import TransactionTestCase
from django.db import transaction
from apps.students.models import Student, Class
from apps.teachers.models import Teacher
from .factories import StudentFactory, ClassFactory, TeacherFactory

class TestDatabaseTransactions(TransactionTestCase):
    """Test database transaction behavior"""
    
    def test_transaction_rollback_on_error(self):
        """Test that transactions roll back on error"""
        initial_count = Student.objects.count()
        
        try:
            with transaction.atomic():
                StudentFactory.create_batch(5)
                raise Exception("Simulated error")
        except Exception:
            pass
        
        # Transaction should be rolled back
        assert Student.objects.count() == initial_count
    
    def test_foreign_key_constraints(self):
        """Test foreign key constraint validation"""
        class_obj = ClassFactory()
        teacher = TeacherFactory()
        
        # This should work
        student = StudentFactory(current_class=class_obj)
        assert student.current_class == class_obj
        
        # This should fail due to foreign key constraint
        with self.assertRaises(Exception):
            Student.objects.create(
                admission_number='S9999',
                first_name='Test',
                last_name='Student',
                current_class_id=9999  # Non-existent class
            )
🌐 API Testing
REST API Test Suite

# apps/api/tests/test_student_api.py
import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.students.models import Student
from .factories import StudentFactory, UserFactory

class TestStudentAPI(APITestCase):
    """Comprehensive API tests for Student endpoints"""
    
    def setUp(self):
        self.admin_user = UserFactory(role='admin')
        self.teacher_user = UserFactory(role='teacher')
        self.student_user = UserFactory(role='student')
        self.student = StudentFactory()
        
        self.client.force_authenticate(user=self.admin_user)
    
    def test_student_list_api(self):
        """Test GET /api/v1/students/"""
        url = reverse('student-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIsInstance(response.data['results'], list)
    
    def test_student_create_api(self):
        """Test POST /api/v1/students/"""
        url = reverse('student-list')
        data = {
            'admission_number': 'S2024102',
            'first_name': 'API',
            'last_name': 'Test',
            'date_of_birth': '2010-06-15',
            'gender': 'female',
            'class_id': self.student.current_class.id,
            'parent': {
                'name': 'Parent Name',
                'email': 'parent@example.com',
                'phone': '+1234567890'
            }
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['admission_number'], 'S2024102')
    
    def test_student_detail_api(self):
        """Test GET /api/v1/students/{id}/"""
        url = reverse('student-detail', kwargs={'pk': self.student.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.student.id)
    
    def test_student_update_api(self):
        """Test PATCH /api/v1/students/{id}/"""
        url = reverse('student-detail', kwargs={'pk': self.student.id})
        data = {
            'first_name': 'Updated Name',
            'phone': '+1987654321'
        }
        
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'Updated Name')
    
    def test_student_delete_api(self):
        """Test DELETE /api/v1/students/{id}/"""
        url = reverse('student-detail', kwargs={'pk': self.student.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)  # Soft delete
    
    def test_api_permissions(self):
        """Test API endpoint permissions"""
        # Teacher should not be able to create students
        self.client.force_authenticate(user=self.teacher_user)
        url = reverse('student-list')
        data = {'admission_number': 'S2024103', 'first_name': 'Test'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
API Authentication Tests

# apps/authentication/tests/test_api_auth.py
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class TestAPIAuthentication(APITestCase):
    """Test API authentication mechanisms"""
    
    def test_token_authentication(self):
        """Test token-based authentication"""
        from rest_framework.authtoken.models import Token
        
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        token = Token.objects.create(user=user)
        
        # Test authenticated request
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get(reverse('student-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_invalid_token(self):
        """Test request with invalid token"""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalidtoken123')
        response = self.client.get(reverse('student-list'))
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_missing_token(self):
        """Test request without token"""
        response = self.client.get(reverse('student-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
🎨 UI Testing with Selenium
Selenium Test Setup

# tests/functional/test_student_management_ui.py
import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from apps.students.models import Student
from .factories import UserFactory, StudentFactory

class TestStudentManagementUI(StaticLiveServerTestCase):
    """UI tests for student management functionality"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.browser = webdriver.Chrome()  # or webdriver.Firefox()
        cls.browser.implicitly_wait(10)
        cls.wait = WebDriverWait(cls.browser, 10)
    
    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()
    
    def setUp(self):
        self.admin_user = UserFactory(role='admin', password='testpass123')
        self.student = StudentFactory()
    
    def login_as_admin(self):
        """Helper method to login as admin"""
        self.browser.get(f'{self.live_server_url}/login/')
        
        username_input = self.browser.find_element(By.NAME, 'username')
        password_input = self.browser.find_element(By.NAME, 'password')
        
        username_input.send_keys(self.admin_user.username)
        password_input.send_keys('testpass123')
        password_input.send_keys(Keys.RETURN)
        
        # Wait for login to complete
        self.wait.until(EC.url_contains('/dashboard/'))
    
    def test_student_list_page(self):
        """Test student list page loads correctly"""
        self.login_as_admin()
        
        # Navigate to student list
        self.browser.get(f'{self.live_server_url}/students/')
        
        # Check page title
        self.assertIn('Students', self.browser.title)
        
        # Check student data is displayed
        student_name = self.browser.find_element(
            By.XPATH, f"//td[contains(text(), '{self.student.first_name}')]"
        )
        self.assertIsNotNone(student_name)
    
    def test_student_creation_flow(self):
        """Test complete student creation flow"""
        self.login_as_admin()
        
        # Navigate to student creation form
        self.browser.get(f'{self.live_server_url}/students/new/')
        
        # Fill out the form
        admission_number = self.browser.find_element(By.NAME, 'admission_number')
        first_name = self.browser.find_element(By.NAME, 'first_name')
        last_name = self.browser.find_element(By.NAME, 'last_name')
        
        admission_number.send_keys('S2024999')
        first_name.send_keys('UI')
        last_name.send_keys('Test')
        
        # Submit the form
        submit_button = self.browser.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()
        
        # Verify success message
        success_message = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'alert-success'))
        )
        self.assertIn('Student created successfully', success_message.text)
        
        # Verify student was created
        self.assertTrue(Student.objects.filter(admission_number='S2024999').exists())
Page Object Model (POM)

# tests/page_objects/student_page.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class StudentListPage:
    """Page Object for Student List page"""
    
    def __init__(self, browser):
        self.browser = browser
        self.wait = WebDriverWait(browser, 10)
    
    # Locators
    SEARCH_INPUT = (By.NAME, 'search')
    STUDENT_TABLE = (By.ID, 'student-table')
    ADD_BUTTON = (By.ID, 'add-student-btn')
    STUDENT_ROWS = (By.CSS_SELECTOR, '#student-table tbody tr')
    
    def load(self):
        self.browser.get('/students/')
        self.wait.until(EC.presence_of_element_located(self.STUDENT_TABLE))
        return self
    
    def search_student(self, query):
        search_input = self.browser.find_element(*self.SEARCH_INPUT)
        search_input.clear()
        search_input.send_keys(query)
        search_input.submit()
        
        # Wait for results to update
        self.wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, '.results-count'),
                'students found'
            )
        )
    
    def get_student_count(self):
        rows = self.browser.find_elements(*self.STUDENT_ROWS)
        return len(rows)
    
    def click_add_student(self):
        self.browser.find_element(*self.ADD_BUTTON).click()
        return StudentFormPage(self.browser)

class StudentFormPage:
    """Page Object for Student Form page"""
    
    def __init__(self, browser):
        self.browser = browser
        self.wait = WebDriverWait(browser, 10)
    
    # Locators
    ADMISSION_NUMBER_INPUT = (By.NAME, 'admission_number')
    FIRST_NAME_INPUT = (By.NAME, 'first_name')
    SUBMIT_BUTTON = (By.XPATH, "//button[@type='submit']")
    
    def fill_form(self, admission_number, first_name, last_name):
        self.browser.find_element(*self.ADMISSION_NUMBER_INPUT).send_keys(admission_number)
        self.browser.find_element(By.NAME, 'first_name').send_keys(first_name)
        self.browser.find_element(By.NAME, 'last_name').send_keys(last_name)
        return self
    
    def submit(self):
        self.browser.find_element(*self.SUBMIT_BUTTON).click()
        self.wait.until(EC.url_contains('/students/'))
        return StudentListPage(self.browser)
📊 Performance Testing
Database Query Optimization Tests

# tests/performance/test_query_performance.py
import time
from django.test import TestCase
from django.db import connection
from django.db.models import Count
from apps.students.models import Student, Attendance
from .factories import StudentFactory, AttendanceFactory

class TestQueryPerformance(TestCase):
    """Performance tests for database queries"""
    
    def setUp(self):
        # Create test data
        self.students = StudentFactory.create_batch(100)
        for student in self.students:
            AttendanceFactory.create_batch(30, student=student)
    
    def test_student_list_query_performance(self):
        """Test that student list query is optimized"""
        start_time = time.time()
        
        # Test optimized query
        with self.assertNumQueries(3):  # Should use limited queries
            students = Student.objects.select_related(
                'current_class', 'section'
            ).prefetch_related(
                'attendance_set'
            ).filter(is_active=True)
            
            # Force query execution
            list(students)
            student_count = students.count()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Query should complete in under 1 second for 100 students
        self.assertLess(query_time, 1.0)
        self.assertEqual(student_count, 100)
    
    def test_attendance_report_performance(self):
        """Test attendance report generation performance"""
        start_time = time.time()
        
        # Generate monthly attendance report
        attendance_data = Attendance.objects.filter(
            date__month=1,
            date__year=2024
        ).values('student').annotate(
            present_count=Count('id', filter=models.Q(status='present')),
            total_days=Count('id')
        )
        
        # Force query execution
        report_data = list(attendance_data)
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Report generation should be fast
        self.assertLess(query_time, 2.0)
        self.assertEqual(len(report_data), 100)
    
    def test_n_plus_one_query_detection(self):
        """Detect and prevent N+1 query problems"""
        with self.assertNumQueries(2):  # Should not make N+1 queries
            students = Student.objects.select_related('current_class').all()
            
            for student in students:
                # This should not trigger additional queries
                class_name = student.current_class.name
                attendance_count = student.attendance_set.count()
API Performance Testing

# tests/performance/test_api_performance.py
import time
from django.urls import reverse
from rest_framework.test import APITestCase
from .factories import StudentFactory, UserFactory

class TestAPIPerformance(APITestCase):
    """Performance tests for API endpoints"""
    
    def setUp(self):
        self.admin_user = UserFactory(role='admin')
        self.students = StudentFactory.create_batch(200)
        self.client.force_authenticate(user=self.admin_user)
    
    def test_student_list_api_performance(self):
        """Test student list API response time"""
        start_time = time.time()
        
        response = self.client.get(reverse('student-list'))
        
        end_time = time.time()
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, 200)
        # API should respond in under 2 seconds for 200 students
        self.assertLess(response_time, 2.0)
        
        # Check response size is reasonable
        response_data = response.json()
        self.assertLess(len(str(response_data)), 100000)  # Under 100KB
    
    def test_api_concurrent_requests(self):
        """Test API performance under concurrent load"""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def make_request(request_id):
            try:
                start_time = time.time()
                response = self.client.get(reverse('student-list'))
                end_time = time.time()
                
                results.put({
                    'request_id': request_id,
                    'response_time': end_time - start_time,
                    'status_code': response.status_code
                })
            except Exception as e:
                errors.put({'request_id': request_id, 'error': str(e)})
        
        # Create 10 concurrent requests
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Analyze results
        response_times = []
        while not results.empty():
            result = results.get()
            response_times.append(result['response_time'])
        
        # Average response time should be reasonable
        avg_response_time = sum(response_times) / len(response_times)
        self.assertLess(avg_response_time, 3.0)
🔒 Security Testing
Authentication & Authorization Tests

# tests/security/test_auth_security.py
import pytest
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .factories import UserFactory, StudentFactory

class TestSecurity(APITestCase):
    """Security tests for authentication and authorization"""
    
    def test_brute_force_protection(self):
        """Test brute force attack protection"""
        url = reverse('login')
        
        # Simulate multiple failed login attempts
        for i in range(10):
            response = self.client.post(url, {
                'username': 'attacker',
                'password': f'wrong_password_{i}'
            })
        
        # After multiple failures, should get rate limited
        response = self.client.post(url, {
            'username': 'attacker',
            'password': 'another_wrong_password'
        })
        
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention"""
        # Attempt SQL injection in search
        url = reverse('student-list')
        response = self.client.get(url, {
            'search': "'; DROP TABLE students; --"
        })
        
        # Should not crash and should handle safely
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Search term should be sanitized, not causing harm
    
    def test_xss_prevention(self):
        """Test Cross-Site Scripting prevention"""
        malicious_script = "<script>alert('XSS')</script>"
        
        # Attempt to inject script in student name
        student = StudentFactory()
        url = reverse('student-detail', kwargs={'pk': student.id})
        
        response = self.client.patch(url, {
            'first_name': malicious_script
        }, format='json')
        
        # Response should sanitize the input
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('<script>', response.data['first_name'])
    
    def test_csrf_protection(self):
        """Test CSRF protection on state-changing operations"""
        admin_user = UserFactory(role='admin')
        self.client.force_authenticate(user=admin_user)
        
        # Try to create student without CSRF token (for session auth)
        url = reverse('student-list')
        response = self.client.post(url, {
            'admission_number': 'S2024999',
            'first_name': 'CSRF'
        }, format='json')
        
        # Should be protected (or work with token auth)
        self.assertIn(response.status_code, [201, 403])
Data Privacy Tests

# tests/security/test_data_privacy.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from .factories import UserFactory, StudentFactory

class TestDataPrivacy(APITestCase):
    """Tests for data privacy and access controls"""
    
    def test_teacher_cannot_access_other_students(self):
        """Test that teachers can only see their assigned students"""
        teacher1 = UserFactory(role='teacher')
        teacher2 = UserFactory(role='teacher')
        
        # Create students for teacher1
        student1 = StudentFactory()
        student1.teachers.add(teacher1.teacher_profile)
        
        # Create students for teacher2
        student2 = StudentFactory()
        student2.teachers.add(teacher2.teacher_profile)
        
        # Teacher1 should only see their students
        self.client.force_authenticate(user=teacher1)
        response = self.client.get(reverse('student-list'))
        
        student_ids = [s['id'] for s in response.data['results']]
        self.assertIn(student1.id, student_ids)
        self.assertNotIn(student2.id, student_ids)
    
    def test_parent_cannot_access_other_children(self):
        """Test that parents can only see their own children"""
        parent1 = UserFactory(role='parent')
        parent2 = UserFactory(role='parent')
        
        student1 = StudentFactory()
        student1.parent = parent1.parent_profile
        student1.save()
        
        student2 = StudentFactory()
        student2.parent = parent2.parent_profile
        student2.save()
        
        # Parent1 should only see their child
        self.client.force_authenticate(user=parent1)
        response = self.client.get(reverse('student-detail', kwargs={'pk': student2.id}))
        
        self.assertEqual(response.status_code, 403)
🧪 Test Data Management
Factory Boy Implementation

# tests/factories.py
import factory
from django.contrib.auth import get_user_model
from apps.students.models import Student, Class, Section
from apps.teachers.models import Teacher
from apps.organization.models import School

User = get_user_model()

class SchoolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = School
    
    name = factory.Sequence(lambda n: f"Test School {n}")
    code = factory.Sequence(lambda n: f"TS{n:03d}")
    address = factory.Faker('address')
    phone = factory.Faker('phone_number')
    email = factory.Faker('email')

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}@test.com")
    email = factory.Sequence(lambda n: f"user{n}@test.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_active = True
    
    class Params:
        admin = factory.Trait(
            role='admin',
            is_staff=True,
            is_superuser=False
        )
        teacher = factory.Trait(role='teacher')
        student = factory.Trait(role='student')
        parent = factory.Trait(role='parent')

class ClassFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Class
    
    name = factory.Sequence(lambda n: f"Grade {n}")
    section = factory.Iterator(['A', 'B', 'C'])
    capacity = 40
    school = factory.SubFactory(SchoolFactory)

class StudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Student
    
    admission_number = factory.Sequence(lambda n: f"S{n:04d}")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    date_of_birth = factory.Faker('date_of_birth', minimum_age=10, maximum_age=18)
    gender = factory.Iterator(['male', 'female'])
    admission_date = factory.Faker('date_this_year')
    current_class = factory.SubFactory(ClassFactory)
    school = factory.SubFactory(SchoolFactory)
    is_active = True
    
    @factory.post_generation
    def teachers(self, create, extracted, **kwargs):
        if not create:
            return
        
        if extracted:
            for teacher in extracted:
                self.teachers.add(teacher)
Fixture Management

# tests/conftest.py
import pytest
from django.db import connections
from django.test.utils import setup_databases, teardown_databases

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Set up test databases"""
    with django_db_blocker.unblock():
        setup_databases(
            verbosity=1,
            interactive=False,
            keepdb=True  # Keep database between test runs for speed
        )

@pytest.fixture
def admin_user(db):
    """Create an admin user for tests"""
    from tests.factories import UserFactory
    return UserFactory(role='admin')

@pytest.fixture
def teacher_user(db):
    """Create a teacher user for tests"""
    from tests.factories import UserFactory
    return UserFactory(role='teacher')

@pytest.fixture
def sample_students(db):
    """Create sample students for tests"""
    from tests.factories import StudentFactory
    return StudentFactory.create_batch(10)
🚀 Running Tests
Basic Test Commands

# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.students

# Run tests with verbosity
python manage.py test --verbosity=2

# Run tests in parallel
python manage.py test --parallel=4

# Run tests without creating test database (faster)
python manage.py test --keepdb

# Run specific test case
python manage.py test apps.students.tests.test_models.TestStudentModel

# Run specific test method
python manage.py test apps.students.tests.test_models.TestStudentModel.test_student_creation
Coverage Reporting

# Install coverage
pip install coverage

# Run tests with coverage
coverage run manage.py test

# Generate report
coverage report
coverage html  # Generate HTML report in htmlcov/

# Coverage with specific modules
coverage run --source='apps.students,apps.teachers' manage.py test

# Generate XML report for CI
coverage xml
Pytest Configuration
ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = tests.py test_*.py *_tests.py
addopts = --tb=short --strict-markers --strict-config
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: integration tests
    ui: UI tests
    performance: performance tests
    security: security tests
Continuous Integration
yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements/test.txt
    - name: Run migrations
      run: |
        python manage.py migrate
    - name: Run tests
      run: |
        python manage.py test --parallel=2
    - name: Generate coverage report
      run: |
        coverage run manage.py test
        coverage xml
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
📈 Test Reports
Generating Test Reports

# Generate JUnit XML reports
python manage.py test --test-runner='xmlrunner.extra.djangotestrunner.XMLTestRunner'

# Generate HTML test report
pip install pytest-html
pytest --html=report.html --self-contained-html

# Generate performance report
python -m cProfile -o profile.prof manage.py test apps.students
snakeviz profile.prof  # Visualize profiling results
Performance Monitoring

# tests/performance/monitor.py
import time
import statistics
from django.test import TestCase
from django.urls import reverse

class PerformanceMonitor:
    """Monitor performance of critical paths"""
    
    @classmethod
    def monitor_critical_paths(cls, test_case):
        critical_paths = [
            ('/api/v1/students/', 'Student List API'),
            ('/api/v1/attendance/', 'Attendance API'),
            ('/admin/', 'Admin Interface'),
        ]
        
        results = {}
        for path, description in critical_paths:
            response_times = []
            
            # Measure multiple requests
            for _ in range(5):
                start_time = time.time()
                response = test_case.client.get(path)
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append(end_time - start_time)
            
            if response_times:
                results[description] = {
                    'average': statistics.mean(response_times),
                    'median': statistics.median(response_times),
                    'min': min(response_times),
                    'max': max(response_times),
                    'count': len(response_times)
                }
        
        return results
🎯 Best Practices
Test Organization

# Good test structure
class TestStudentModel:
    def test_creation(self): ...
    def test_validation(self): ...
    def test_methods(self): ...
    def test_relationships(self): ...

class TestStudentViews:
    def test_list_view(self): ...
    def test_detail_view(self): ...
    def test_create_view(self): ...
    def test_permissions(self): ...
Test Naming Convention

# Good test names
def test_student_creation_with_valid_data(self): ...
def test_student_should_require_admission_number(self): ...
def test_teacher_cannot_access_other_students(self): ...
def test_api_returns_401_for_unauthenticated_users(self): ...

# Avoid vague names
def test_student(self): ...  # Too vague
def test_thing(self): ...    # Meaningless
Test Data Management

# Use factories instead of direct ORM calls
# Good
student = StudentFactory()

# Avoid
student = Student.objects.create(
    admission_number='S001',
    first_name='Test',
    # ... many fields
)