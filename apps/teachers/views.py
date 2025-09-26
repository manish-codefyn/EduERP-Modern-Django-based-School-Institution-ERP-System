# teachers/views/export_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import update_session_auth_hash, login
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import  PermissionRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.contrib.messages.views import SuccessMessageMixin
from apps.core.mixins import DirectorRequiredMixin
from apps.core.utils import get_user_institution 
from .models import Teacher
from .forms import TeacherForm
from apps.organization.models import Institution
from utils.utils import export_pdf_response, render_to_pdf, qr_generate
import csv
from io import StringIO

# Import the service classes
from .idcard import TeacherIDCardGenerator


def teacher_id_card_png(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    organization = Institution.objects.filter(is_active=True).first()

    logo = organization.logo.path if organization and organization.logo else None
    stamp = organization.stamp.path if organization and organization.stamp else None

    generator = TeacherIDCardGenerator(
        teacher=teacher,
        logo_path=logo,
        stamp_path=stamp,
    )
    return generator.get_id_card_response()

class TeacherListView(DirectorRequiredMixin, ListView):
    model = Teacher
    template_name = "teachers/teacher_list.html"
    context_object_name = "teachers"
    paginate_by = 20

    def get_queryset(self):
        """Filter teachers by user's institution and apply search filters"""
        queryset = Teacher.objects.filter(
            institution=get_user_institution(self.request.user)
        )

        # Search functionality
        search_query = self.request.GET.get("search")
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query)
                | Q(middle_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(employee_id__icontains=search_query)
                | Q(qualification__icontains=search_query)
                | Q(specialization__icontains=search_query)
                | Q(subjects__name__icontains=search_query)
            ).distinct()

        # Organization type filter
        org_type = self.request.GET.get("organization_type")
        if org_type:
            queryset = queryset.filter(organization_type=org_type)

        # Department filter
        department = self.request.GET.get("department")
        if department:
            queryset = queryset.filter(department=department)

        # Designation filter
        designation = self.request.GET.get("designation")
        if designation:
            queryset = queryset.filter(designation=designation)

        # Faculty type filter
        faculty_type = self.request.GET.get("faculty_type")
        if faculty_type:
            queryset = queryset.filter(faculty_type=faculty_type)

        # Class teacher filter
        is_class_teacher = self.request.GET.get("is_class_teacher")
        if is_class_teacher:
            if is_class_teacher.lower() == 'true':
                queryset = queryset.filter(is_class_teacher=True)
            elif is_class_teacher.lower() == 'false':
                queryset = queryset.filter(is_class_teacher=False)

        # Status filter (active/inactive)
        status = self.request.GET.get("status")
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)

        return queryset.select_related("institution").prefetch_related("subjects").order_by("last_name", "first_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context["organization_type_filter"] = self.request.GET.get("organization_type", "")
        context["department_filter"] = self.request.GET.get("department", "")
        context["designation_filter"] = self.request.GET.get("designation", "")
        context["faculty_type_filter"] = self.request.GET.get("faculty_type", "")
        context["is_class_teacher_filter"] = self.request.GET.get("is_class_teacher", "")
        context["status_filter"] = self.request.GET.get("status", "")

        # Add filter choices to context
        context["organization_types"] = Teacher.ORGANIZATION_TYPE_CHOICES
        context["departments"] = Teacher.DEPARTMENT_CHOICES
        context["designations"] = Teacher.DESIGNATION_CHOICES
        context["faculty_types"] = [
            ('regular', 'Regular'),
            ('visiting', 'Visiting'),
            ('guest', 'Guest'),
            ('contract', 'Contract'),
            ('part_time', 'Part Time'),
        ]

        # Teacher fields for export checkboxes
        # Format: (field_name, Label)
        context["teacher_fields"] = [
            ("first_name", "First Name"),
            ("middle_name", "Middle Name"),
            ("last_name", "Last Name"),
            ("email", "Email"),
            ("employee_id", "Employee ID"),
            ("qualification", "Qualification"),
            ("specialization", "Specialization"),
            ("subjects", "Subjects"),
            ("department", "Department"),
            ("designation", "Designation"),
            ("faculty_type", "Faculty Type"),
            ("organization_type", "Organization Type"),
            ("is_class_teacher", "Class Teacher"),
            ("status", "Status"),
            # add any other fields you want to export
        ]

        # Teacher stats for dashboard use
        context["teacher_statistics"] = Teacher.get_statistics(
            Teacher.objects.filter(institution=get_user_institution(self.request.user))
        )

        return context


class TeacherDetailView(DirectorRequiredMixin, DetailView):
    model = Teacher
    template_name = "teachers/teacher_detail.html"
    context_object_name = "teacher"

    def get_queryset(self):
        """Only show teachers from the same institution"""
        return Teacher.objects.filter(institution=get_user_institution(self.request.user))



class TeacherCreateView( DirectorRequiredMixin, CreateView):
    model = Teacher
    form_class = TeacherForm
    template_name = "teachers/teacher_form.html"
    
    permission_required = "teachers.add_teacher"

    def get_form_kwargs(self):
        """Pass the user's institution to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['institution'] = get_user_institution(self.request.user)
        return kwargs

    def form_valid(self, form):
        """Set the institution automatically before saving and show message"""
        form.instance.institution = get_user_institution(self.request.user)
        response = super().form_valid(form)
        
        # Add custom success message
        full_name = f"{form.instance.first_name} {form.instance.last_name}"
        messages.success(self.request, f'Teacher "{full_name}" created successfully.')
        return response

    def get_success_url(self):
        return reverse_lazy("teacher_detail", kwargs={"pk": self.object.pk})


class TeacherUpdateView( DirectorRequiredMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = "teachers/teacher_form.html"
    permission_required = "teachers.change_teacher"

    def get_queryset(self):
        """Only allow editing teachers from the same institution"""
        return Teacher.objects.filter(institution=get_user_institution(self.request.user))

    def get_form_kwargs(self):
        """Pass the user's institution to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['institution'] = get_user_institution(self.request.user)
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Teacher "{self.object.first_name} {self.object.last_name}" updated successfully.'
        )
        return response

    def get_success_url(self):
        return reverse_lazy("teacher_detail", kwargs={"pk": self.object.pk})


class TeacherDeleteView( DirectorRequiredMixin, DeleteView):
    model = Teacher
    template_name = "teachers/teacher_confirm_delete.html"
    permission_required = "teachers.delete_teacher"

    def get_queryset(self):
        """Only allow deleting teachers from the same institution"""
        return Teacher.objects.filter(institution=get_user_institution(self.request.user))

    def get_success_url(self):
        return reverse_lazy("teacher_list")

    def delete(self, request, *args, **kwargs):
        """Add success message for deletion"""
        teacher = self.get_object()
        # Use first_name + last_name or get_full_name() to avoid KeyError
        messages.success(
            self.request,
            f'Teacher "{teacher.get_full_name()}" deleted successfully.'
        )
        return super().delete(request, *args, **kwargs)