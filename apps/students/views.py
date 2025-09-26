from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.http import JsonResponse

from .models import (Student, Guardian, StudentMedicalInfo, StudentAddress,
                     StudentDocument, StudentHistory, StudentTransport, 
                     StudentHostel, StudentIdentification)
from .forms import (
    StudentForm, GuardianForm, StudentMedicalInfoForm, 
    StudentAddressForm, StudentDocumentForm, StudentFilterForm,
    StudentStatusForm, StudentClassForm, StudentHistoryForm, 
    StudentTransportForm, StudentHostelForm, StudentIdentificationForm
)
from apps.academics.models import Section, Class
from apps.organization.models import Institution
from .idcard import StudentIDCardGenerator  
from apps.core.utils import get_user_institution  
from apps.core.mixins import DirectorRequiredMixin,TeacherRequiredMixin,StudentManagementRequiredMixin
import logging
logger = logging.getLogger(__name__)


def load_sections(request):
    """Return sections for a selected class (used via AJAX)."""
    class_id = request.GET.get('class_id')

    if not class_id:  # Prevent empty UUID error
        return JsonResponse([], safe=False)

    try:
        sections = Section.objects.filter(class_name_id=class_id).order_by('name')
    except Exception:
        return JsonResponse([], safe=False)

    return JsonResponse(list(sections.values('id', 'name')), safe=False)



class StudentListView(StudentManagementRequiredMixin, ListView):
    model = Student
    template_name = 'students/student_list.html'
    context_object_name = 'students'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'current_class', 'section', 'academic_year', 'institution'
        ).order_by('roll_number')
        
        self.search_form = StudentFilterForm(self.request.GET)
        if self.search_form.is_valid():
            cd = self.search_form.cleaned_data

            if cd.get('admission_number'):
                queryset = queryset.filter(admission_number__icontains=cd['admission_number'])
            if cd.get('first_name'):
                queryset = queryset.filter(first_name__icontains=cd['first_name'])
            if cd.get('last_name'):
                queryset = queryset.filter(last_name__icontains=cd['last_name'])
            if cd.get('student_class'):
                queryset = queryset.filter(current_class_id=cd['student_class'])
            if cd.get('section'):
                queryset = queryset.filter(section_id=cd['section'])
            if cd.get('academic_year'):
                queryset = queryset.filter(academic_year_id=cd['academic_year'])
            if cd.get('status'):
                queryset = queryset.filter(status=cd['status'])

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = self.search_form

        # Get user's institution for filtering
        user_institution = get_user_institution(self.request.user)
        
        # Stats - filter by user's institution if available
        if user_institution:
            context['total_students'] = Student.objects.filter(institution=user_institution).count()
            context['active_students'] = Student.objects.filter(status='ACTIVE', institution=user_institution).count()
            context['inactive_students'] = Student.objects.exclude(status='ACTIVE').filter(institution=user_institution).count()
            context['male_students'] = Student.objects.filter(gender='M', institution=user_institution).count()
            context['female_students'] = Student.objects.filter(gender='F', institution=user_institution).count()
            context['unspecified_gender'] = Student.objects.filter(
                Q(gender__isnull=True) | Q(gender=''), institution=user_institution
            ).count()
        else:
            # If no institution found, show all students
            context['total_students'] = Student.objects.count()
            context['active_students'] = Student.objects.filter(status='ACTIVE').count()
            context['inactive_students'] = Student.objects.exclude(status='ACTIVE').count()
            context['male_students'] = Student.objects.filter(gender='M').count()
            context['female_students'] = Student.objects.filter(gender='F').count()
            context['unspecified_gender'] = Student.objects.filter(
                Q(gender__isnull=True) | Q(gender='')
            ).count()

        # Check completion status for each student
        for student in context['students']:
            student.completion_status = self.get_completion_status(student)
        
        # Add data needed for export modal
        context.update(self.get_export_context_data())
            
        return context

    def get_completion_status(self, student):
        """Calculate completion percentage for student data"""
        total_steps = 6
        completed_steps = 1  # Basic info always filled

        if student.guardians.exists():
            completed_steps += 1
        if hasattr(student, 'medical_info'):
            completed_steps += 1
        if student.addresses.exists():
            completed_steps += 1
        if student.documents.exists():
            completed_steps += 1
        if hasattr(student, 'identification'):
            completed_steps += 1

        return {
            "percentage": (completed_steps / total_steps) * 100,
            "completed_steps": completed_steps,
            "total_steps": total_steps
        }


    def get_export_context_data(self):
        """Get context data needed for the export modal"""
        user_institution = get_user_institution(self.request.user)
        
        # Filter classes and sections by user's institution if available
        if user_institution:
            classes = Class.objects.filter(institution=user_institution)
            sections = Section.objects.filter(institution=user_institution)
        else:
            classes = Class.objects.all()
            sections = Section.objects.all()
            
        return {
            'classes': classes,
            'sections': sections,
            'status_choices': Student.STATUS_CHOICES,
            'gender_choices': Student.GENDER_CHOICES,
            'blood_group_choices': Student.BLOOD_GROUP_CHOICES,
            'admission_type_choices': Student.ADMISSION_TYPE_CHOICES,
            'category_choices': Student.CATEGORY_CHOICES,
            'religion_choices': Student.RELIGION_CHOICES,
            'student_fields': [
                ('admission_number', 'Admission Number'),
                ('first_name', 'First Name'),
                ('last_name', 'Last Name'),
                ('current_class', 'Class'),
                ('section', 'Section'),
                ('academic_year', 'Academic Year'),
                ('status', 'Status'),
                ('gender', 'Gender'),
                ('blood_group', 'Blood Group'),
                ('admission_type', 'Admission Type'),
                ('category', 'Category'),
                ('religion', 'Religion'),
                ('has_hostel', 'Hostel Student'),
                ('has_disability', 'Has Disability'),
                ('has_transport', 'Uses Transport'),
                ('email', 'Email'),
                ('mobile', 'Mobile'),
                ('date_of_birth', 'Date of Birth'),
                ('created_at', 'Created At'),
            ]
        }
    
    def get_completion_status(self, student):
        """Calculate completion percentage for student data"""
        total_steps = 5  # Basic info, guardian, medical, address, documents
        completed_steps = 1  # Basic info is always completed
        
        # Check guardian
        if student.guardians.exists():
            completed_steps += 1
            
        # Check medical info
        if hasattr(student, 'medical_info'):
            completed_steps += 1
            
        # Check address
        if student.addresses.exists():
            completed_steps += 1
            
        # Check documents
        if student.documents.exists():
            completed_steps += 1
            
        return {
            'percentage': (completed_steps / total_steps) * 100,
            'completed_steps': completed_steps,
            'total_steps': total_steps
        }


class StudentCreateView(StudentManagementRequiredMixin,PermissionRequiredMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    permission_required = "students.add_student"

    def get_form_kwargs(self):
        """Pass logged-in user to the form for auto-detecting institution"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        """Set initial values for the form"""
        initial = super().get_initial()
        try:
            from academics.models import AcademicYear
            current_year = AcademicYear.objects.filter(is_current=True).first()
            if current_year:
                initial['academic_year'] = current_year
        except ImportError:
            pass
        return initial

    def form_valid(self, form):
        """Handle valid form submission with logging and messages"""
        try:
            response = super().form_valid(form)
            messages.success(self.request, _('Student created successfully!'))
            # Log creation by current user
            logger.info(f"Student created: {self.object.admission_number} by {self.request.user}")
            return response
        except Exception as e:
            logger.error(f"Error creating student: {str(e)}")
            messages.error(self.request, _('An error occurred while creating the student. Please try again.'))
            return self.form_invalid(form)

    def form_invalid(self, form):
        """Handle invalid form submission"""
        logger.warning(f"Student form validation failed: {form.errors}")
        messages.error(self.request, _('Please correct the errors below.'))
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add additional context to the template"""
        context = super().get_context_data(**kwargs)
        try:
            from academics.models import AcademicYear
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                context['academic_years'] = AcademicYear.objects.filter(
                    institution=user_institution
                ).order_by('-start_date')
            else:
                context['academic_years'] = AcademicYear.objects.all().order_by('-start_date')
        except ImportError:
            context['academic_years'] = []
        return context

    def get_success_url(self):
        return reverse('students:student_onboarding', kwargs={'pk': self.object.pk})


class StudentUpdateView(StudentManagementRequiredMixin,PermissionRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Student updated successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('students:student_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context

class StudentDetailView(StudentManagementRequiredMixin, DetailView):
    model = Student
    template_name = 'students/student_detail.html'
    context_object_name = 'student'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object

        # Related data
        context['guardians'] = student.guardians.all()
        context['medical_info'] = getattr(student, 'medical_info', None)
        context['addresses'] = student.addresses.all()
        context['documents'] = student.documents.all()
        context['transport'] = getattr(student, 'transport', None)
        context['hostel'] = getattr(student, 'hostel', None)
        context['history'] = student.history.all()
        context['identification'] = getattr(student, 'identification', None)

        # Specific guardians
        context['primary_parent'] = student.guardians.filter(is_primary=True).first()
        context['father'] = student.guardians.filter(relation="FATHER").first()
        context['mother'] = student.guardians.filter(relation="MOTHER").first()

        # Emergency contact (from medical info if available)
        medical_info = getattr(student, 'medical_info', None)
        if medical_info and (medical_info.emergency_contact_name or medical_info.emergency_contact_phone):
            context['emergency_contact'] = medical_info
        else:
            context['emergency_contact'] = None

        # Completion
        context['completion_status'] = self.get_completion_status(student)
        return context
    
    def get_completion_status(self, student):
        """Calculate completion percentage for student data"""
        total_steps = 6  # Added identification step
        completed_steps = 1  # Basic info

        if student.guardians.exists():
            completed_steps += 1
        if hasattr(student, 'medical_info'):
            completed_steps += 1
        if student.addresses.exists():
            completed_steps += 1
        if student.documents.exists():
            completed_steps += 1
        if hasattr(student, 'identification'):
            completed_steps += 1

        return {
            'percentage': (completed_steps / total_steps) * 100,
            'completed_steps': completed_steps,
            'total_steps': total_steps
        }


class StudentOnboardingView(StudentManagementRequiredMixin,PermissionRequiredMixin, TemplateView):
    template_name = 'students/onboarding.html'
    permission_required = "students.add_student"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        
        completion_status = self.get_completion_status(student)
        context['student'] = student
        context['completion_status'] = completion_status
        context['next_step'] = self.get_next_step(student, completion_status)
        
        return context
    
    def get_completion_status(self, student):
        total_steps = 9  # Added identification
        steps = {
            'basic_info': True,
            'guardian': student.guardians.exists(),
            'medical': hasattr(student, 'medical_info'),
            'address': student.addresses.exists(),
            'documents': student.documents.exists(),
            'transport': hasattr(student, 'transport'),
            'hostel': hasattr(student, 'hostel'),
            'history': student.history.exists(),
            'identification': hasattr(student, 'identification'),
        }
        completed_steps = sum(1 for step in steps.values() if step)
        
        return {
            'percentage': (completed_steps / total_steps) * 100,
            'completed_steps': completed_steps,
            'total_steps': total_steps,
            'steps': steps
        }
    
    def get_next_step(self, student, completion_status):
        if not completion_status['steps']['guardian']:
            return ('guardian', _('Add Guardian Information'), reverse('students:guardian_create', kwargs={'pk': student.pk}))
        elif not completion_status['steps']['medical']:
            return ('medical', _('Add Medical Information'), reverse('students:medical_create', kwargs={'pk': student.pk}))
        elif not completion_status['steps']['address']:
            return ('address', _('Add Address Information'), reverse('students:address_create', kwargs={'pk': student.pk}))
        elif not completion_status['steps']['documents']:
            return ('documents', _('Upload Documents'), reverse('students:document_upload', kwargs={'pk': student.pk}))
        elif not completion_status['steps']['identification']:
            return ('identification', _('Add Identification Information'), reverse('students:identification_create', kwargs={'pk': student.pk}))
        elif not completion_status['steps']['transport']:
            return ('transport', _('Add Transport Information'), reverse('students:transport_create', kwargs={'pk': student.pk}))
        elif not completion_status['steps']['hostel']:
            return ('hostel', _('Add Hostel Information'), reverse('students:hostel_create', kwargs={'pk': student.pk}))
        elif not completion_status['steps']['history']:
            return ('history', _('Add Academic History'), reverse('students:history_create', kwargs={'pk': student.pk}))
        else:
            return (None, _('All information completed!'), reverse('students:student_detail', kwargs={'pk': student.pk}))



class GuardianCreateView(StudentManagementRequiredMixin,PermissionRequiredMixin, CreateView):
    model = Guardian
    form_class = GuardianForm
    template_name = 'students/guardian/guardian_form.html'
    permission_required = "students.add_student"
    
    def get_initial(self):
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        return {'student': student}
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Guardian information added successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('students:student_onboarding', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context
    
    
class GuardianUpdateView(StudentManagementRequiredMixin,PermissionRequiredMixin, UpdateView):
    model = Guardian
    form_class = GuardianForm
    template_name = 'students/guardian_form.html'
    permission_required = "students.add_student"
    
    def get_object(self, queryset=None):
        # Get guardian of the student
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        return get_object_or_404(Guardian, student=student)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Guardian information updated successfully!'))
        return response

    def get_success_url(self):
        return reverse('students:student_onboarding', kwargs={'pk': self.kwargs['pk']})
   
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context


class MedicalInfoCreateView(StudentManagementRequiredMixin,PermissionRequiredMixin, CreateView):
    model = StudentMedicalInfo
    form_class = StudentMedicalInfoForm
    template_name = 'students/medical_form.html'
    permission_required = "students.add_student"
    
    def get_initial(self):
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        return {'student': student}
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Medical information added successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('students:student_onboarding', kwargs={'pk': self.kwargs['pk']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context


class MedicalInfoUpdateView(StudentManagementRequiredMixin,PermissionRequiredMixin, UpdateView):
    model = StudentMedicalInfo
    form_class = StudentMedicalInfoForm
    template_name = 'students/medical_form.html'
    permission_required = "students.add_student"
    
    def get_object(self, queryset=None):
        # Get the Student instance
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        # Return the linked medical object
        return get_object_or_404(StudentMedicalInfo, student=student)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Medical information updated successfully!")
        return response

    def get_success_url(self):
        return reverse('students:student_onboarding', kwargs={'pk': self.kwargs['pk']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context
    
    
class AddressCreateView(StudentManagementRequiredMixin,PermissionRequiredMixin, CreateView):
    model = StudentAddress
    form_class = StudentAddressForm
    template_name = 'students/address_form.html'
    permission_required = "students.add_student"
    
    def get_initial(self):
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        return {'student': student}
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Address information added successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('students:student_onboarding', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context
    
    
class AddressUpdateView(StudentManagementRequiredMixin, PermissionRequiredMixin,UpdateView):
    model = StudentAddress
    form_class = StudentAddressForm
    template_name = 'students/address_form.html'
    permission_required = "students.add_student"

    def get_object(self, queryset=None):
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        return get_object_or_404(StudentAddress, student=student)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Address updated successfully!")
        return response

    def get_success_url(self):
        return reverse('students:student_onboarding', kwargs={'pk': self.kwargs['pk']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context  
    
    
class StudentDocumentListView(StudentManagementRequiredMixin,PermissionRequiredMixin, ListView):
    model = StudentDocument
    template_name = "students/documents/document_list.html"
    context_object_name = "documents"
    permission_required = "students.add_student"

    def get_queryset(self):
        self.student = get_object_or_404(Student, pk=self.kwargs["pk"])
        return StudentDocument.objects.filter(student=self.student)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.student
        documents = self.get_queryset()

        verified_count = documents.filter(is_verified=True).count()
        pending_count = documents.filter(is_verified=False).count()
        rejected_count = documents.filter(is_verified=None).count()  # Optional, if you track rejection

        doc_type_counts = {
            doc_type: documents.filter(doc_type=doc_type).count()
            for doc_type, _ in StudentDocument.DOCUMENT_TYPE_CHOICES
        }

        recent_documents = documents.order_by('-uploaded_at')[:5]

        context.update({
            'student': student,
            'documents': documents,
            'verified_count': verified_count,
            'pending_count': pending_count,
            'rejected_count': rejected_count,
            'doc_type_counts': doc_type_counts,
            'recent_documents': recent_documents,
        })
        return context

    
class StudentDocumentUploadView(StudentManagementRequiredMixin,PermissionRequiredMixin, CreateView):
    model = StudentDocument
    form_class = StudentDocumentForm
    template_name = 'students/documents/document_form.html'
    permission_required = "students.add_student"

    def get_initial(self):
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        return {'student': student}

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Remove the student field so user cannot edit it
        if 'student' in form.fields:
            form.fields.pop('student')
        return form

    def form_valid(self, form):
        # Assign the student automatically
        form.instance.student = get_object_or_404(Student, pk=self.kwargs['pk'])
        response = super().form_valid(form)
        messages.success(self.request, _('Document uploaded successfully!'))
        return response

    def get_success_url(self):
        return reverse('students:student_onboarding', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context

    
class StudentDocumentDeleteView(StudentManagementRequiredMixin,PermissionRequiredMixin, DeleteView):
    model = StudentDocument
    template_name = "students/documents/document_confirm_delete.html"
    context_object_name = "document"
    permission_required = "students.delete_student"

    def get_object(self, queryset=None):
        student = get_object_or_404(Student, pk=self.kwargs['student_pk'])
        return get_object_or_404(StudentDocument, pk=self.kwargs['doc_pk'], student=student)

    def get_success_url(self):
        return reverse_lazy("students:document_list", kwargs={"pk": self.kwargs['student_pk']})
    


class StudentDocumentUpdateView(StudentManagementRequiredMixin,PermissionRequiredMixin, UpdateView):
    model = StudentDocument
    form_class = StudentDocumentForm
    template_name = "students/documents/document_form.html"
    permission_required = "students.add_student"
    
    def get_object(self, queryset=None):
        return get_object_or_404(
            StudentDocument,
            pk=self.kwargs["pk"],
            student_id=self.kwargs["student_pk"]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["student"] = get_object_or_404(Student, pk=self.kwargs["student_pk"])
        return context

    def get_success_url(self):
        return reverse_lazy("students:document_list", kwargs={"pk": self.kwargs["student_pk"]})

    
class StudentStatusUpdateView(StudentManagementRequiredMixin, PermissionRequiredMixin,UpdateView):
    model = Student
    form_class = StudentStatusForm
    template_name = 'students/student_status_form.html'
    permission_required = "students.update_student"
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Student status updated successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('students:student_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context



class StudentClassUpdateView(StudentManagementRequiredMixin,PermissionRequiredMixin,UpdateView):
    model = Student
    form_class = StudentClassForm
    template_name = 'students/student_class_form.html'
    permission_required = "students.update_student"
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Student class updated successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('students:student_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context

class StudentDeleteView(DirectorRequiredMixin,PermissionRequiredMixin, DeleteView):
    model = Student
    template_name = 'students/student_confirm_delete.html'
    success_url = reverse_lazy('students:student_list')
    permission_required = "students.delete_student"
    
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('Student deleted successfully!'))
        return response
    
    
# -------------------- Transport Views --------------------
class TransportCreateView(StudentManagementRequiredMixin,CreateView):
    model = StudentTransport
    form_class = StudentTransportForm
    template_name = 'students/transport_form.html'

    def get_initial(self):
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        return {'student': student}
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Transport information added successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('students:student_onboarding', kwargs={'pk': self.kwargs['pk']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context

class TransportUpdateView(StudentManagementRequiredMixin, UpdateView):
    model = StudentTransport
    form_class = StudentTransportForm
    template_name = 'students/transport_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Transport information updated successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('students:student_detail', kwargs={'pk': self.object.student.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context

# -------------------- Hostel Views --------------------
class HostelCreateView(StudentManagementRequiredMixin, CreateView):
    model = StudentHostel
    form_class = StudentHostelForm
    template_name = 'students/hostel_form.html'
    
    def get_initial(self):
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        return {'student': student}
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Hostel information added successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('students:student_onboarding', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context
    
    
class HostelUpdateView(StudentManagementRequiredMixin,UpdateView):
    model = StudentHostel
    form_class = StudentHostelForm
    template_name = 'students/hostel_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Hostel information updated successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('students:student_detail', kwargs={'pk': self.object.student.pk})\
            
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context

# -------------------- Academic History Views --------------------
class HistoryCreateView(StudentManagementRequiredMixin, CreateView):
    model = StudentHistory
    form_class = StudentHistoryForm
    template_name = 'students/history_form.html'
    
    def get_initial(self):
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        # Set current academic year and class as default
        initial = {'student': student}
        
        if student.academic_year:
            initial['academic_year'] = student.academic_year
        if student.current_class:
            initial['class_name'] = student.current_class
        if student.section:
            initial['section'] = student.section
        if student.roll_number:
            initial['roll_number'] = student.roll_number
            
        return initial
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Academic history added successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('students:student_onboarding', kwargs={'pk': self.kwargs['pk']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context

class HistoryUpdateView(StudentManagementRequiredMixin, UpdateView):
    model = StudentHistory
    form_class = StudentHistoryForm
    template_name = 'students/history_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Academic history updated successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('students:student_detail', kwargs={'pk': self.object.student.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context
    

def student_id_card_png(request, pk):
    student = get_object_or_404(Student, pk=pk)
    organization = Institution.objects.filter(is_active=True).first()

    logo = organization.logo.path if organization and organization.logo else None

    generator = StudentIDCardGenerator(
        student=student,
        logo_path=logo,
    )
    return generator.get_id_card_response()



class StudentIdentificationCreateView(StudentManagementRequiredMixin, CreateView):
    model = StudentIdentification
    form_class = StudentIdentificationForm
    template_name = 'students/add_identification.html'

    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student, pk=self.kwargs['pk'])
        # Redirect if identification already exists
        if hasattr(self.student, 'identification'):
            return redirect('students:identification_update', pk=self.student.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.student = self.student
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('students:student_detail', kwargs={'pk': self.student.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = self.student
        return context


class StudentIdentificationUpdateView(StudentManagementRequiredMixin, UpdateView):
    model = StudentIdentification
    form_class = StudentIdentificationForm
    template_name = 'students/edit_identification.html'

    def get_object(self, queryset=None):
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        return getattr(student, 'identification')

    def get_success_url(self):
        return reverse_lazy('students:student_detail', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_object_or_404(Student, pk=self.kwargs['pk'])
        return context