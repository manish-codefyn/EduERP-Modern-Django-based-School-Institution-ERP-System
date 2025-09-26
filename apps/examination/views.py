import csv
import xlsxwriter
from io import BytesIO, StringIO
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Avg, Count,Min,Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect,render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.utils.translation import gettext_lazy as _
from apps.core.mixins import TeacherRequiredMixin
from apps.core.utils import get_user_institution
from utils.utils import render_to_pdf, export_pdf_response



from .models import ExamType, Exam, ExamSubject, ExamResult
from .forms import ExamTypeForm, ExamForm, ExamSubjectForm, ExamResultForm


from django.views.generic import TemplateView
from django.db.models import Count, Avg, F
from django.utils import timezone

import json

class ExamDashboardView(TeacherRequiredMixin,TemplateView):
    """
    Class-based view to render the main examination dashboard with stats and charts.
    """
    template_name = 'examination/exam_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. KPI Cards Data
        total_exams = Exam.objects.count()
        total_students_with_results = ExamResult.objects.values('student').distinct().count()
        total_subjects_defined = ExamSubject.objects.values('subject').distinct().count()
        
        # Calculate overall pass percentage
        total_results_count = ExamResult.objects.count()
        passed_results_count = ExamResult.objects.filter(
            marks_obtained__gte=F('exam_subject__pass_marks')
        ).count()
        overall_pass_percentage = round(
            (passed_results_count / total_results_count) * 100 if total_results_count > 0 else 0, 2
        )

        # 2. Data for Charts
        # Grade Distribution (Doughnut Chart)
        grade_distribution_query = ExamResult.objects.values('grade').annotate(
            count=Count('grade')
        ).order_by('grade')
        grade_labels = [item['grade'] for item in grade_distribution_query if item['grade']]
        grade_data = [item['count'] for item in grade_distribution_query if item['grade']]

        # Subject Performance (Bar Chart) - Average marks obtained per subject
        subject_performance_query = ExamResult.objects.values(
            'exam_subject__subject__name'
        ).annotate(
            avg_score=Avg('marks_obtained')
        ).order_by('-avg_score')[:10]  # Top 10 performing subjects
        
        subject_labels = [item['exam_subject__subject__name'] for item in subject_performance_query]
        subject_data = [round(float(item['avg_score']), 2) for item in subject_performance_query]

        # 3. Data for Tables
        # Upcoming Exams
        upcoming_exams = Exam.objects.filter(
            start_date__gte=timezone.now().date()
        ).order_by('start_date')[:5]
        
        # Recently Published Results
        recent_results = Exam.objects.filter(
            is_published=True
        ).order_by('-end_date')[:5]

        context.update({
            'total_exams': total_exams,
            'total_students_with_results': total_students_with_results,
            'total_subjects_defined': total_subjects_defined,
            'overall_pass_percentage': overall_pass_percentage,
            'grade_labels': json.dumps(grade_labels),
            'grade_data': json.dumps(grade_data),
            'subject_labels': json.dumps(subject_labels),
            'subject_data': json.dumps(subject_data),
            'upcoming_exams': upcoming_exams,
            'recent_results': recent_results,
            'title': 'Examination Dashboard'
        })
        
        return context

class ExamTypeListView(TeacherRequiredMixin, ListView):
    model = ExamType
    template_name = 'examination/type/examtype_list.html'
    context_object_name = 'exam_types'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter by user's institution
        institution = get_user_institution(user)
        if institution:
            queryset = queryset.filter(institution=institution)
        
        # Apply filters
        institution_filter = self.request.GET.get('institution')
        is_active = self.request.GET.get('is_active')
        search_query = self.request.GET.get('search')
        
        if institution_filter:
            queryset = queryset.filter(institution_id=institution_filter)
        if is_active is not None:
            queryset = queryset.filter(is_active=(is_active == 'true'))
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        return queryset.select_related('institution').order_by('institution__name', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add statistics
        queryset = self.get_queryset()
        context['total_records'] = queryset.count()
        context['active_count'] = queryset.filter(is_active=True).count()
        context['inactive_count'] = queryset.filter(is_active=False).count()
        
        return context
    

class ExamTypeCreateView(TeacherRequiredMixin, CreateView):
    model = ExamType
    form_class = ExamTypeForm
    template_name = 'examination/type/examtype_form.html'
    success_url = reverse_lazy('examination:exam_type_list')

    def form_valid(self, form):
        # Automatically assign the institution based on logged-in user
        institution = get_user_institution(self.request.user)
        if institution:
            form.instance.institution = institution

        # Ensure code is unique per institution
        if ExamType.objects.filter(
            institution=institution, code=form.cleaned_data['code']
        ).exists():
            form.add_error('code', 'This code already exists for your institution.')
            return self.form_invalid(form)

        response = super().form_valid(form)
        messages.success(self.request, _('Exam type created successfully!'))
        return response


class ExamTypeUpdateView(TeacherRequiredMixin, UpdateView):
    model = ExamType
    form_class = ExamTypeForm  # form does NOT include 'institution'
    template_name = 'examination/type/examtype_form.html'
    success_url = reverse_lazy('examination:exam_type_list')

    def form_valid(self, form):
        # Ensure code is unique per institution, excluding current instance
        institution = get_user_institution(self.request.user)
        if ExamType.objects.filter(
            institution=institution, code=form.cleaned_data['code']
        ).exclude(pk=form.instance.pk).exists():
            form.add_error('code', 'This code already exists for your institution.')
            return self.form_invalid(form)

        messages.success(self.request, _('Exam type updated successfully!'))
        return super().form_valid(form)



class ExamTypeDeleteView( TeacherRequiredMixin, DeleteView):
    model = ExamType
    template_name = 'examination/type/examtype_confirm_delete.html'
    success_url = reverse_lazy('examination:exam_type_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Exam type deleted successfully!'))
        return super().delete(request, *args, **kwargs)



class ExamListView( TeacherRequiredMixin, ListView):
    model = Exam
    template_name = 'examination/exam_list.html'
    context_object_name = 'exams'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Filter by user's institution
        institution = get_user_institution(user)
        if institution:
            queryset = queryset.filter(institution=institution)

        # Filters
        institution_filter = self.request.GET.get('institution')
        academic_year = self.request.GET.get('academic_year')
        exam_type = self.request.GET.get('exam_type')
        status = self.request.GET.get('status')
        search_query = self.request.GET.get('search')

        if institution_filter:
            queryset = queryset.filter(institution_id=institution_filter)
        if academic_year:
            queryset = queryset.filter(academic_year_id=academic_year)
        if exam_type:
            queryset = queryset.filter(exam_type_id=exam_type)
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
            )

        queryset = queryset.select_related('institution', 'exam_type', 'academic_year').order_by('-start_date')

        # Filter by dynamic status if requested
        if status:
            now = timezone.now().date()
            if status == 'upcoming':
                queryset = queryset.filter(start_date__gt=now)
            elif status == 'ongoing':
                queryset = queryset.filter(start_date__lte=now, end_date__gte=now)
            elif status == 'completed':
                queryset = queryset.filter(end_date__lt=now)
            elif status == 'cancelled':
                # Assuming you have an is_cancelled BooleanField
                queryset = queryset.filter(is_cancelled=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        context['total_records'] = queryset.count()

        now = timezone.now().date()
        context['upcoming_count'] = queryset.filter(start_date__gt=now).count()
        context['ongoing_count'] = queryset.filter(start_date__lte=now, end_date__gte=now).count()
        context['completed_count'] = queryset.filter(end_date__lt=now).count()
        # Add cancelled count if you have is_cancelled field
        # context['cancelled_count'] = queryset.filter(is_cancelled=True).count()

        # Average duration in days
        exams_with_duration = queryset.filter(start_date__isnull=False, end_date__isnull=False)
        if exams_with_duration.exists():
            total_duration = sum((exam.end_date - exam.start_date).days for exam in exams_with_duration)
            context['avg_duration'] = round(total_duration / exams_with_duration.count(), 1)
        else:
            context['avg_duration'] = 0

        return context
    

class ExamCreateView( TeacherRequiredMixin, CreateView):
    model = Exam
    form_class = ExamForm
    template_name = 'examination/exam_form.html'
    success_url = reverse_lazy('examination:exam_list')

    def form_valid(self, form):
        # Automatically assign the institution based on logged-in user
        institution = get_user_institution(self.request.user)
        if institution:
            form.instance.institution = institution

        # Optional: Ensure exam name is unique per institution and academic year
        if Exam.objects.filter(
            institution=institution,
            name=form.cleaned_data['name'],
            academic_year=form.cleaned_data['academic_year']
        ).exists():
            form.add_error('name', 'This exam already exists for your institution and academic year.')
            return self.form_invalid(form)

        response = super().form_valid(form)
        messages.success(self.request, _('Exam created successfully!'))
        return response


class ExamUpdateView( TeacherRequiredMixin, UpdateView):
    model = Exam
    form_class = ExamForm  # form does NOT include 'institution'
    template_name = 'examination/exam_form.html'
    success_url = reverse_lazy('examination:exam_list')

    def form_valid(self, form):
        # Ensure exam name is unique per institution and academic year, excluding current instance
        institution = get_user_institution(self.request.user)
        if Exam.objects.filter(
            institution=institution,
            name=form.cleaned_data['name'],
            academic_year=form.cleaned_data['academic_year']
        ).exclude(pk=form.instance.pk).exists():
            form.add_error('name', 'This exam already exists for your institution and academic year.')
            return self.form_invalid(form)

        messages.success(self.request, _('Exam updated successfully!'))
        return super().form_valid(form)


class ExamDetailView( TeacherRequiredMixin, DetailView):
    model = Exam
    template_name = 'examination/exam_detail.html'
    context_object_name = 'exam'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exam = self.get_object()
        today = timezone.now().date()
        
        # Get subjects with related data
        subjects = exam.subjects.select_related('subject').prefetch_related('results')
        context['subjects'] = subjects
        context['today'] = today
        
        # Calculate statistics
        context['subject_count'] = subjects.count()
        context['result_count'] = ExamResult.objects.filter(exam_subject__exam=exam).count()
        
        # Calculate completed and upcoming subjects
        context['completed_subjects'] = subjects.filter(exam_date__lt=today).count()
        context['upcoming_subjects'] = subjects.filter(exam_date__gte=today).count()
        
        # Calculate progress percentage
        if subjects.count() > 0:
            context['progress_percentage'] = round((context['completed_subjects'] / subjects.count()) * 100)
        else:
            context['progress_percentage'] = 0
        
        # Calculate average marks if results exist
        if context['result_count'] > 0:
            avg_marks = ExamResult.objects.filter(
                exam_subject__exam=exam
            ).aggregate(Avg('marks_obtained'))['marks_obtained__avg']
            context['avg_marks'] = round(avg_marks, 2)
        else:
            context['avg_marks'] = 0
            
        return context


class ExamDeleteView( TeacherRequiredMixin, DeleteView):
    model = Exam
    template_name = 'examination/exam_confirm_delete.html'
    success_url = reverse_lazy('examination:exam_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Exam deleted successfully!'))
        return super().delete(request, *args, **kwargs)



class ExamSubjectListView( TeacherRequiredMixin, ListView):
    model = ExamSubject
    template_name = 'examination/subject/examsubject_list.html'
    context_object_name = 'exam_subjects'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Filter by user's institution via exam
        institution = get_user_institution(user)
        if institution:
            queryset = queryset.filter(exam__institution=institution)

        # Filters
        exam_filter = self.request.GET.get('exam')
        subject_filter = self.request.GET.get('subject')
        exam_date = self.request.GET.get('exam_date')
        search_query = self.request.GET.get('search')

        if exam_filter:
            queryset = queryset.filter(exam_id=exam_filter)
        if subject_filter:
            queryset = queryset.filter(subject_id=subject_filter)
        if exam_date:
            queryset = queryset.filter(exam_date=exam_date)
        if search_query:
            queryset = queryset.filter(
                Q(subject__name__icontains=search_query) |
                Q(exam__name__icontains=search_query)
            )

        return queryset.select_related('exam', 'subject').order_by('exam__start_date', 'exam_date', 'start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        context['total_records'] = queryset.count()

        now = timezone.now().date()
        context['upcoming_count'] = queryset.filter(exam_date__gt=now).count()
        context['ongoing_count'] = queryset.filter(exam_date=now).count()
        context['completed_count'] = queryset.filter(exam_date__lt=now).count()

        # Average max marks
        if queryset.exists():
            total_max_marks = sum(subject.max_marks for subject in queryset)
            context['avg_max_marks'] = round(total_max_marks / queryset.count(), 2)
        else:
            context['avg_max_marks'] = 0

        return context


class ExamSubjectDetailView( TeacherRequiredMixin, DetailView):
    model = ExamSubject
    template_name = 'examination/subject/examsubject_detail.html'
    context_object_name = 'exam_subject'

    def get_queryset(self):
        """Limit to the user's institution."""
        user = self.request.user
        institution = get_user_institution(user)
        queryset = super().get_queryset().select_related('exam', 'subject', 'exam__exam_type', 'exam__academic_year')
        if institution:
            queryset = queryset.filter(exam__institution=institution)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exam_subject = self.object

        # Basic info
        context['exam_name'] = exam_subject.exam.name
        context['subject_name'] = exam_subject.subject.name
        context['exam_type'] = exam_subject.exam.exam_type.name
        context['academic_year'] = exam_subject.exam.academic_year.name
        context['max_marks'] = exam_subject.max_marks
        context['pass_marks'] = exam_subject.pass_marks
        context['exam_date'] = exam_subject.exam_date
        context['start_time'] = exam_subject.start_time
        context['end_time'] = exam_subject.end_time

        # Results count
        context['results_count'] = exam_subject.results.count()

        # Status based on date
        today = timezone.now().date()
        if exam_subject.exam_date > today:
            context['status'] = 'Upcoming'
        elif exam_subject.exam_date == today:
            context['status'] = 'Ongoing'
        else:
            context['status'] = 'Completed'

        # Duration
        if exam_subject.start_time and exam_subject.end_time:
            context['duration'] = timezone.datetime.combine(timezone.now(), exam_subject.end_time) - \
                                  timezone.datetime.combine(timezone.now(), exam_subject.start_time)
        else:
            context['duration'] = None

        return context


class ExamSubjectCreateView( TeacherRequiredMixin, CreateView):
    model = ExamSubject
    form_class = ExamSubjectForm
    template_name = 'examination/subject/examsubject_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def get_success_url(self):
        return reverse_lazy('examination:exam_detail', kwargs={'pk': self.object.exam.id})
    
    def form_valid(self, form):
        messages.success(self.request, _('Exam subject added successfully!'))
        return super().form_valid(form)


class ExamSubjectUpdateView( TeacherRequiredMixin, UpdateView):
    model = ExamSubject
    form_class = ExamSubjectForm
    template_name = 'examination/subject/examsubject_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def get_success_url(self):
        return reverse_lazy('examination:exam_detail', kwargs={'pk': self.object.exam.id})
    
    def form_valid(self, form):
        messages.success(self.request, _('Exam subject updated successfully!'))
        return super().form_valid(form)


class ExamSubjectDeleteView( TeacherRequiredMixin, DeleteView):
    model = ExamSubject
    template_name = 'examination/subject/examsubject_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('examination:exam_detail', kwargs={'pk': self.object.exam.id})
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Exam subject deleted successfully!'))
        return super().delete(request, *args, **kwargs)


class ExamResultListView( TeacherRequiredMixin, ListView):
    model = ExamResult
    template_name = 'examination/result/examresult_list.html'
    context_object_name = 'results'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Filter by user's institution via exam
        institution = get_user_institution(user)
        if institution:
            queryset = queryset.filter(exam_subject__exam__institution=institution)

        # Apply filters
        exam_subject = self.request.GET.get('exam_subject')
        student = self.request.GET.get('student')
        exam = self.request.GET.get('exam')
        min_marks = self.request.GET.get('min_marks')
        max_marks = self.request.GET.get('max_marks')
        search_query = self.request.GET.get('search')

        if exam_subject:
            queryset = queryset.filter(exam_subject_id=exam_subject)
        if student:
            queryset = queryset.filter(student_id=student)
        if exam:
            queryset = queryset.filter(exam_subject__exam_id=exam)
        if min_marks:
            queryset = queryset.filter(marks_obtained__gte=min_marks)
        if max_marks:
            queryset = queryset.filter(marks_obtained__lte=max_marks)
        if search_query:
            queryset = queryset.filter(
                Q(student__user__first_name__icontains=search_query) |
                Q(student__user__last_name__icontains=search_query) |
                Q(student__admission_number__icontains=search_query) |
                Q(exam_subject__subject__name__icontains=search_query)
            )

        return queryset.select_related(
            'exam_subject', 'exam_subject__exam', 'exam_subject__subject',
            'student', 'student__user'
        ).order_by('-exam_subject__exam__start_date', 'student__user__first_name')


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add statistics
        queryset = self.get_queryset()
        context['total_records'] = queryset.count()
        
        if context['total_records'] > 0:
            # Calculate statistics
            stats = queryset.aggregate(
                avg_marks=Avg('marks_obtained'),
                max_marks=Max('marks_obtained'),
                min_marks=Min('marks_obtained'),
                total_marks=Sum('marks_obtained')
            )
            
            context['avg_marks'] = round(stats['avg_marks'], 2)
            context['max_marks'] = stats['max_marks']
            context['min_marks'] = stats['min_marks']
            context['total_marks'] = stats['total_marks']
            
            # Count passed/failed (assuming passing marks are 40)
            passing_marks = 40
            context['passed_count'] = queryset.filter(marks_obtained__gte=passing_marks).count()
            context['failed_count'] = queryset.filter(marks_obtained__lt=passing_marks).count()
        else:
            context.update({
                'avg_marks': 0,
                'max_marks': 0,
                'min_marks': 0,
                'total_marks': 0,
                'passed_count': 0,
                'failed_count': 0
            })
        
        return context
    

class ExamResultCreateView( TeacherRequiredMixin, CreateView):
    model = ExamResult
    form_class = ExamResultForm
    template_name = 'examination/result/examresult_form.html'
    success_url = reverse_lazy('examination:exam_result_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # Pass user to form
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, _('Exam result added successfully!'))
        return super().form_valid(form)

class ExamResultDetailView( TeacherRequiredMixin, DetailView):
    model = ExamResult
    template_name = 'examination/result/examresult_detail.html'
    context_object_name = 'result'


class ExamResultUpdateView( TeacherRequiredMixin, UpdateView):
    model = ExamResult
    form_class = ExamResultForm
    template_name = 'examination/examresult_form.html'
    success_url = reverse_lazy('examination:exam_result_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, _('Exam result updated successfully!'))
        return super().form_valid(form)


class ExamResultDeleteView( TeacherRequiredMixin, DeleteView):
    model = ExamResult
    template_name = 'examination/examresult_confirm_delete.html'
    success_url = reverse_lazy('examination:exam_result_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Exam result deleted successfully!'))
        return super().delete(request, *args, **kwargs)


class ExamExportView( TeacherRequiredMixin, ListView):
    model = Exam
    context_object_name = 'exams'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Exam.objects.filter(institution=institution).select_related('institution', 'exam_type', 'academic_year')
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        exam_type = request.GET.get('exam_type')
        academic_year = request.GET.get('academic_year')
        status = request.GET.get('status')
        
        queryset = self.get_queryset()
        
        # Apply filters
        if exam_type:
            queryset = queryset.filter(exam_type_id=exam_type)
        if academic_year:
            queryset = queryset.filter(academic_year_id=academic_year)
        if status:
            queryset = queryset.filter(status=status)
        
        # Build filename
        filename = f"exams_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Build data rows
        rows = []
        for exam in queryset:
            rows.append({
                "name": exam.name,
                "code": exam.exam_type.code,
                "exam_type": exam.exam_type.name,
                "academic_year": exam.academic_year.name,
                "start_date": exam.start_date.strftime('%Y-%m-%d') if exam.start_date else 'N/A',
                "end_date": exam.end_date.strftime('%Y-%m-%d') if exam.end_date else 'N/A',
                "status": exam.get_status_display,
                "total_subjects": exam.subjects.count(),
                "description": exam.exam_type.description,
                "created_at": exam.created_at.strftime('%Y-%m-%d %H:%M'),
            })

        organization = get_user_institution(request.user)
        
        if format_type == 'csv':
            return self.export_csv(rows, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(rows, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(rows, filename, organization, queryset.count())
        else:
            return HttpResponse("Invalid format specified", status=400)
    
    def export_csv(self, rows, filename, organization):
        """Export data to CSV format"""
        buffer = StringIO()
        writer = csv.writer(buffer)
        
        # Write header
        writer.writerow([
            'Exam Name', 'Code', 'Exam Type', 'Academic Year', 'Start Date',
            'End Date', 'Status', 'Total Subjects', 'Description', 'Created At'
        ])
        
        # Write data rows
        for row in rows:
            writer.writerow([
                row['name'],
                row['code'],
                row['exam_type'],
                row['academic_year'],
                row['start_date'],
                row['end_date'],
                row['status'],
                row['total_subjects'],
                row['description'],
                row['created_at'],
            ])
        
        # Add summary
        writer.writerow([])
        writer.writerow(['Total Exams:', len(rows)])
        
        # Calculate statistics
        status_counts = {}
        for row in rows:
            status = row['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            writer.writerow([f'{status} Count:', count])
        
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, rows, filename, organization):
        """Export data to Excel format"""
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Exams')
            
            # Add formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#3b5998',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True
            })
            
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})
            center_format = workbook.add_format({'align': 'center'})
            
            # Write headers
            headers = [
                'Exam Name', 'Code', 'Exam Type', 'Academic Year', 'Start Date',
                'End Date', 'Status', 'Total Subjects', 'Description', 'Created At'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['name'])
                worksheet.write(row_idx, 1, row_data['code'])
                worksheet.write(row_idx, 2, row_data['exam_type'])
                worksheet.write(row_idx, 3, row_data['academic_year'])
                worksheet.write(row_idx, 4, row_data['start_date'], date_format)
                worksheet.write(row_idx, 5, row_data['end_date'], date_format)
                worksheet.write(row_idx, 6, row_data['status'], center_format)
                worksheet.write(row_idx, 7, row_data['total_subjects'], center_format)
                worksheet.write(row_idx, 8, row_data['description'])
                worksheet.write(row_idx, 9, row_data['created_at'], datetime_format)
            
            # Adjust column widths
            worksheet.set_column('A:A', 25)  # Exam Name
            worksheet.set_column('B:B', 15)  # Code
            worksheet.set_column('C:C', 20)  # Exam Type
            worksheet.set_column('D:D', 15)  # Academic Year
            worksheet.set_column('E:F', 12)  # Dates
            worksheet.set_column('G:G', 15)  # Status
            worksheet.set_column('H:H', 15)  # Total Subjects
            worksheet.set_column('I:I', 30)  # Description
            worksheet.set_column('J:J', 18)  # Created At
            
            # Add summary
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Exams:')
            worksheet.write(summary_row, 1, len(rows))
            
            # Calculate status counts
            status_counts = {}
            for row in rows:
                status = row['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            for status, count in status_counts.items():
                summary_row += 1
                worksheet.write(summary_row, 0, f'{status} Count:')
                worksheet.write(summary_row, 1, count)
            
            summary_row += 2
            worksheet.write(summary_row, 0, 'Organization:')
            worksheet.write(summary_row, 1, organization.name if organization else 'N/A')
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Export Date:')
            worksheet.write(summary_row, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))
        
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response
    
    def export_pdf(self, rows, filename, organization, total_count):
        """Export data to PDF format"""
        # Calculate statistics
        status_counts = {}
        for row in rows:
            status = row['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        context = {
            "exams": rows,
            "total_count": total_count,
            "status_counts": status_counts,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Exams Export",
            "columns": [
                {'name': 'Exam Name', 'width': '20%'},
                {'name': 'Code', 'width': '10%'},
                {'name': 'Exam Type', 'width': '15%'},
                {'name': 'Academic Year', 'width': '12%'},
                {'name': 'Start Date', 'width': '10%'},
                {'name': 'End Date', 'width': '10%'},
                {'name': 'Status', 'width': '10%'},
                {'name': 'Subjects', 'width': '8%'},
            ]
        }
        
        pdf_bytes = render_to_pdf("examination/export/exams_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)


class ExamTypeExportView( TeacherRequiredMixin, ListView):
    model = ExamType
    context_object_name = 'exam_types'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return ExamType.objects.filter(institution=institution).select_related('institution')
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        is_active = request.GET.get('is_active')

        queryset = self.get_queryset()

        # Apply filters
        if is_active is not None:
            queryset = queryset.filter(is_active=(is_active.lower() == 'true'))

        # Build filename
        filename = f"exam_types_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Build data rows
        rows = []
        for exam_type in queryset:
            rows.append({
                "name": exam_type.name,
                "code": exam_type.code,
                "description": exam_type.description,
                "is_active": "Active" if exam_type.is_active else "Inactive",
                "created_at": exam_type.updated_at.strftime('%Y-%m-%d %H:%M') if exam_type.updated_at else "N/A",

            })

        organization = get_user_institution(request.user)

        if format_type == 'csv':
            return self.export_csv(rows, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(rows, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(rows, filename, organization, queryset.count())
        else:
            return HttpResponse("Invalid format specified", status=400)

    # ---------------- CSV EXPORT ----------------
    def export_csv(self, rows, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        # Header
        writer.writerow(['Name', 'Code', 'Description', 'Status', 'Created At'])

        # Data
        for row in rows:
            writer.writerow([
                row['name'],
                row['code'],
                row['description'],
                row['is_active'],
                row['created_at'],
            ])

        # Summary
        writer.writerow([])
        writer.writerow(['Total Exam Types:', len(rows)])

        status_counts = {"Active": 0, "Inactive": 0}
        for row in rows:
            status_counts[row['is_active']] += 1

        writer.writerow(['Active Count:', status_counts['Active']])
        writer.writerow(['Inactive Count:', status_counts['Inactive']])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    # ---------------- EXCEL EXPORT ----------------
    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()

        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Exam Types')

            # Styles
            header_format = workbook.add_format({
                'bold': True, 'bg_color': '#3b5998',
                'font_color': 'white', 'border': 1,
                'align': 'center', 'valign': 'vcenter',
                'text_wrap': True
            })
            center_format = workbook.add_format({'align': 'center'})
            datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})

            headers = ['Name', 'Code', 'Description', 'Status', 'Created At']

            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['name'])
                worksheet.write(row_idx, 1, row_data['code'])
                worksheet.write(row_idx, 2, row_data['description'])
                worksheet.write(row_idx, 3, row_data['is_active'], center_format)
                worksheet.write(row_idx, 4, row_data['created_at'], datetime_format)

            # Column widths
            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:B', 15)
            worksheet.set_column('C:C', 40)
            worksheet.set_column('D:D', 12)
            worksheet.set_column('E:E', 20)

            # Summary
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Exam Types:')
            worksheet.write(summary_row, 1, len(rows))

            status_counts = {"Active": 0, "Inactive": 0}
            for row in rows:
                status_counts[row['is_active']] += 1

            summary_row += 1
            worksheet.write(summary_row, 0, 'Active Count:')
            worksheet.write(summary_row, 1, status_counts['Active'])

            summary_row += 1
            worksheet.write(summary_row, 0, 'Inactive Count:')
            worksheet.write(summary_row, 1, status_counts['Inactive'])

            summary_row += 2
            worksheet.write(summary_row, 0, 'Organization:')
            worksheet.write(summary_row, 1, organization.name if organization else 'N/A')

            summary_row += 1
            worksheet.write(summary_row, 0, 'Export Date:')
            worksheet.write(summary_row, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    # ---------------- PDF EXPORT ----------------
    def export_pdf(self, rows, filename, organization, total_count):
        status_counts = {"Active": 0, "Inactive": 0}
        for row in rows:
            status_counts[row['is_active']] += 1

        context = {
            "exam_types": rows,
            "total_count": total_count,
            "status_counts": status_counts,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Exam Types Export",
            "columns": [
                {'name': 'Name', 'width': '20%'},
                {'name': 'Code', 'width': '15%'},
                {'name': 'Description', 'width': '45%'},
                {'name': 'Status', 'width': '10%'},
                {'name': 'Created At', 'width': '10%'},
            ]
        }

        pdf_bytes = render_to_pdf("examination/export/exam_types_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)


class ExamResultExportView( TeacherRequiredMixin, ListView):
    model = ExamResult
    context_object_name = 'results'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return ExamResult.objects.filter(
            exam_subject__exam__institution=institution
        ).select_related(
            'exam_subject',
            'exam_subject__exam',
            'exam_subject__subject',
            'student',
            'student__user'
        )

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        exam_subject = request.GET.get('exam_subject')
        exam = request.GET.get('exam')
        student = request.GET.get('student')

        queryset = self.get_queryset()

        # Filters
        if exam_subject:
            queryset = queryset.filter(exam_subject_id=exam_subject)
        if exam:
            queryset = queryset.filter(exam_subject__exam_id=exam)
        if student:
            queryset = queryset.filter(student_id=student)

        filename = f"exam_results_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Build rows
        rows = []
        for result in queryset:
            percentage = round((result.marks_obtained / result.exam_subject.max_marks) * 100, 2) \
                if result.exam_subject.max_marks else 0
            rows.append({
                "student_name": result.student.full_name,
                "admission_number": result.student.admission_number,
        
                "academic_year": result.exam_subject.exam.academic_year.name,
                "duration": result.exam_subject.exam.duration,
                "status": result.exam_subject.exam.get_status_display,
                "subject_name": result.exam_subject.subject.name,
                "max_marks": result.exam_subject.max_marks,
                "marks_obtained": result.marks_obtained,
                "percentage": percentage,
                "grade": result.grade,
                "remarks": result.remarks,
                "exam_date": result.exam_subject.exam_date.strftime('%Y-%m-%d') if result.exam_subject.exam_date else 'N/A',
                "created_at": result.created_at.strftime('%Y-%m-%d %H:%M'),
            })

        organization = get_user_institution(request.user)

        if format_type == 'csv':
            return self.export_csv(rows, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(rows, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(rows, filename,result, organization, queryset.count())
        else:
            return HttpResponse("Invalid format specified", status=400)

    # ---------------- CSV EXPORT ----------------
    def export_csv(self, rows, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        writer.writerow([
            'Student Name', 'Admission Number', 'Exam Name', 'Subject',
            'Max Marks', 'Marks Obtained', 'Percentage', 'Grade', 'Remarks',
            'Exam Date', 'Created At'
        ])

        for row in rows:
            writer.writerow([
                row['student_name'],
                row['admission_number'],
                row['exam_name'],
                row['subject_name'],
                row['max_marks'],
                row['marks_obtained'],
                row['percentage'],
                row['grade'],
                row['remarks'],
                row['exam_date'],
                row['created_at'],
            ])

        # Summary
        writer.writerow([])
        writer.writerow(['Total Results:', len(rows)])
        if rows:
            avg_percentage = sum(r['percentage'] for r in rows) / len(rows)
            writer.writerow(['Average Percentage:', round(avg_percentage, 2)])
            writer.writerow(['Highest Marks:', max(r['marks_obtained'] for r in rows)])
            writer.writerow(['Lowest Marks:', min(r['marks_obtained'] for r in rows)])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    # ---------------- EXCEL EXPORT ----------------
    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Exam Results')

            header_format = workbook.add_format({
                'bold': True, 'bg_color': '#3b5998', 'font_color': 'white',
                'border': 1, 'align': 'center', 'valign': 'vcenter',
                'text_wrap': True
            })
            center_format = workbook.add_format({'align': 'center'})
            percent_format = workbook.add_format({'num_format': '0.00%', 'align': 'center'})
            datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})

            headers = [
                'Student Name', 'Admission Number', 'Exam Name', 'Subject',
                'Max Marks', 'Marks Obtained', 'Percentage', 'Grade', 'Remarks',
                'Exam Date', 'Created At'
            ]

            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, row in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row['student_name'])
                worksheet.write(row_idx, 1, row['admission_number'])
                worksheet.write(row_idx, 2, row['exam_name'])
                worksheet.write(row_idx, 3, row['subject_name'])
                worksheet.write(row_idx, 4, row['max_marks'], center_format)
                worksheet.write(row_idx, 5, row['marks_obtained'], center_format)
                worksheet.write(row_idx, 6, row['percentage'] / 100, percent_format)
                worksheet.write(row_idx, 7, row['grade'], center_format)
                worksheet.write(row_idx, 8, row['remarks'])
                worksheet.write(row_idx, 9, row['exam_date'])
                worksheet.write(row_idx, 10, row['created_at'], datetime_format)

            # Column widths
            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:B', 18)
            worksheet.set_column('C:D', 25)
            worksheet.set_column('E:F', 12)
            worksheet.set_column('G:H', 12)
            worksheet.set_column('I:I', 30)
            worksheet.set_column('J:K', 18)

            # Summary
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Results:')
            worksheet.write(summary_row, 1, len(rows))

            if rows:
                avg_percentage = sum(r['percentage'] for r in rows) / len(rows)
                worksheet.write(summary_row + 1, 0, 'Average Percentage:')
                worksheet.write(summary_row + 1, 1, round(avg_percentage, 2))
                worksheet.write(summary_row + 2, 0, 'Highest Marks:')
                worksheet.write(summary_row + 2, 1, max(r['marks_obtained'] for r in rows))
                worksheet.write(summary_row + 3, 0, 'Lowest Marks:')
                worksheet.write(summary_row + 3, 1, min(r['marks_obtained'] for r in rows))

            worksheet.write(summary_row + 5, 0, 'Organization:')
            worksheet.write(summary_row + 5, 1, organization.name if organization else 'N/A')
            worksheet.write(summary_row + 6, 0, 'Export Date:')
            worksheet.write(summary_row + 6, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    # ---------------- PDF EXPORT ----------------
    def export_pdf(self, rows, filename,result, organization, total_count):
        context = {
            "results": rows,
            "exam_name": result.exam_subject.exam.name,
            "exam_type": result.exam_subject.exam.exam_type.name,
            "duration": result.exam_subject.exam.duration,
            "academic_year": result.exam_subject.exam.academic_year.name,
            "status": result.exam_subject.exam.get_status_display,
            "total_count": total_count,
            "average_percentage": round(sum(r['percentage'] for r in rows) / len(rows), 2) if rows else 0,
            "highest_marks": max((r['marks_obtained'] for r in rows), default=0),
            "lowest_marks": min((r['marks_obtained'] for r in rows), default=0),
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Exam Results Export",
            "columns": [
                {'name': 'Student Name', 'width': '15%'},
                {'name': 'Admission #', 'width': '12%'},
                {'name': 'Exam', 'width': '15%'},
                {'name': 'Subject', 'width': '15%'},
                {'name': 'Max', 'width': '6%'},
                {'name': 'Obtained', 'width': '8%'},
                {'name': '%', 'width': '6%'},
                {'name': 'Grade', 'width': '6%'},
                {'name': 'Remarks', 'width': '12%'},
                {'name': 'Exam Date', 'width': '10%'},
            ]
        }

        pdf_bytes = render_to_pdf("examination/export/exam_results_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)


class ExamSubjectExportView( TeacherRequiredMixin, ListView):
    model = ExamSubject
    context_object_name = 'exam_subjects'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return ExamSubject.objects.filter(
            exam__institution=institution
        ).select_related('exam', 'subject', 'exam__exam_type', 'exam__academic_year')

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        exam_id = request.GET.get('exam')
        subject_id = request.GET.get('subject')
        search = request.GET.get('search')

        queryset = self.get_queryset()

        # Apply filters
        if exam_id:
            queryset = queryset.filter(exam_id=exam_id)
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if search:
            queryset = queryset.filter(subject__name__icontains=search)

        # Build filename
        filename = f"exam_subjects_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Build data rows
        rows = []
        for es in queryset:
            rows.append({
                "exam": es.exam.name,
                "subject": es.subject.name,
                "exam_type": es.exam.exam_type.name,
                "academic_year": es.exam.academic_year.name,
                "max_marks": es.max_marks,
                "pass_marks": es.pass_marks,
                "exam_date": es.exam_date.strftime('%Y-%m-%d') if es.exam_date else 'N/A',
                "start_time": es.start_time.strftime('%H:%M') if es.start_time else 'N/A',
                "end_time": es.end_time.strftime('%H:%M') if es.end_time else 'N/A',
                "duration": es.exam.duration if es.exam.duration and es.exam.duration else None,
                "results_count": es.results.count(),
                "created_at": es.created_at if es.created_at else 'N/A'
            })

        organization = get_user_institution(request.user)

        if format_type == 'csv':
            return self.export_csv(rows, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(rows, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(rows, filename, organization, queryset.count())
        else:
            return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, rows, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        # Header
        writer.writerow([
            'Exam', 'Subject', 'Exam Type', 'Academic Year',
            'Max Marks', 'Pass Marks', 'Exam Date', 'Start Time', 'End Time',
            'Results Count', 'Created At'
        ])

        for row in rows:
            writer.writerow([
                row['exam'], row['subject'], row['exam_type'], row['academic_year'],
                row['max_marks'], row['pass_marks'], row['exam_date'],
                row['start_time'], row['end_time'], row['results_count'], row['created_at']
            ])

        writer.writerow([])
        writer.writerow(['Total Subjects:', len(rows)])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Exam Subjects')
            header_format = workbook.add_format({'bold': True, 'bg_color': '#3b5998', 'font_color': 'white', 'border': 1, 'align': 'center'})
            center_format = workbook.add_format({'align': 'center'})

            headers = [
                'Exam', 'Subject', 'Exam Type', 'Academic Year',
                'Max Marks', 'Pass Marks', 'Exam Date', 'Start Time', 'End Time',
                'Results Count', 'Created At'
            ]
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, row in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row['exam'])
                worksheet.write(row_idx, 1, row['subject'])
                worksheet.write(row_idx, 2, row['exam_type'])
                worksheet.write(row_idx, 3, row['academic_year'])
                worksheet.write(row_idx, 4, row['max_marks'], center_format)
                worksheet.write(row_idx, 5, row['pass_marks'], center_format)
                worksheet.write(row_idx, 6, row['exam_date'])
                worksheet.write(row_idx, 7, row['start_time'])
                worksheet.write(row_idx, 8, row['end_time'])
                worksheet.write(row_idx, 9, row['results_count'], center_format)
                worksheet.write(row_idx, 10, row['created_at'])

            # Summary
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Subjects:')
            worksheet.write(summary_row, 1, len(rows))
            worksheet.write(summary_row + 1, 0, 'Organization:')
            worksheet.write(summary_row + 1, 1, organization.name if organization else 'N/A')
            worksheet.write(summary_row + 2, 0, 'Export Date:')
            worksheet.write(summary_row + 2, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))

        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, rows, filename, organization, total_count):
        status_counts = {}  # Optional: if you want stats based on results
        context = {
            "exam_subjects": rows,
            "total_count": total_count,
            "export_date": timezone.now(),
            "organization": organization,
            "title": "Exam Subjects Export",
            "columns": [
                {'name': 'Exam', 'width': '15%'},
                {'name': 'Subject', 'width': '15%'},
                {'name': 'Exam Type', 'width': '15%'},
                {'name': 'Academic Year', 'width': '10%'},
                {'name': 'Max Marks', 'width': '10%'},
                {'name': 'Pass Marks', 'width': '10%'},
                {'name': 'Exam Date', 'width': '10%'},
                {'name': 'Start-End Time', 'width': '15%'},
            ]
        }
        pdf_bytes = render_to_pdf("examination/export/exam_subjects_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)




class ExamResultReportCardExportView( TeacherRequiredMixin, DetailView):
    model = ExamResult
    context_object_name = "exam_result"
    template_name = "examination/export/report_card_base.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        format_type = request.GET.get("format", "pdf").lower()
        result = self.object
        
        # Get organization/institution
        organization = get_user_institution(request.user)
        
        # Prepare comprehensive result data
        result_data = self.prepare_report_card_data(result, organization)
        
        filename = f"report_card_{result.student.user.get_full_name()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if format_type == "csv":
            return self.export_csv(result_data, filename)
        elif format_type == "excel":
            return self.export_excel(result_data, filename)
        elif format_type == "pdf":
            return self.export_pdf(result_data, filename)
        elif format_type == "html":
            return self.export_html(result_data)
        return HttpResponse("Invalid format specified", status=400)

    def prepare_report_card_data(self, result, organization):
        """Prepare comprehensive data for report card"""
        # Get all results for this student in the same exam
        exam_results = ExamResult.objects.filter(
            student=result.student,
            exam_subject__exam=result.exam_subject.exam
        ).select_related('exam_subject__subject', 'exam_subject__exam')
        
        # Calculate overall performance
        total_marks_obtained = sum(float(res.marks_obtained) for res in exam_results)
        total_max_marks = sum(float(res.exam_subject.max_marks) for res in exam_results)
        overall_percentage = (total_marks_obtained / total_max_marks * 100) if total_max_marks > 0 else 0
        
        # Determine overall grade
        if overall_percentage >= 90:
            overall_grade = 'A+'
        elif overall_percentage >= 80:
            overall_grade = 'A'
        elif overall_percentage >= 70:
            overall_grade = 'B+'
        elif overall_percentage >= 60:
            overall_grade = 'B'
        elif overall_percentage >= 50:
            overall_grade = 'C'
        elif overall_percentage >= 40:
            overall_grade = 'D'
        else:
            overall_grade = 'F'

        return {
            "student": {
                "name": result.student.user.get_full_name(),
                "admission_number": result.student.admission_number,
                "class": getattr(result.student.current_class, 'name', 'N/A'),
                "section": getattr(result.student.section, 'name', 'N/A'),
                "roll_number": getattr(result.student, 'roll_number', 'N/A'),
            },
            "exam": {
                "name": result.exam_subject.exam.name,
                "type": result.exam_subject.exam.exam_type.name,
                "academic_year": result.exam_subject.exam.academic_year.name,
                "start_date": result.exam_subject.exam.start_date,
                "end_date": result.exam_subject.exam.end_date,
            },
            "organization": {
                "name": organization.name if organization else "Educational Institution",
                "logo": organization.logo.url if organization and organization.logo else None,
                "address": organization.address if organization else "",
            },
            "subjects": [
                {
                    "name": res.exam_subject.subject.name,
                    "code": res.exam_subject.subject.code,
                    "marks_obtained": float(res.marks_obtained),
                    "max_marks": float(res.exam_subject.max_marks),
                    "percentage": (float(res.marks_obtained) / float(res.exam_subject.max_marks)) * 100,
                    "grade": res.grade,
                    "pass_marks": float(res.exam_subject.pass_marks),
                    "status": "Pass" if float(res.marks_obtained) >= float(res.exam_subject.pass_marks) else "Fail",
                    "remarks": res.remarks or "Good",
                }
                for res in exam_results
            ],
            "overall": {
                "total_obtained": total_marks_obtained,
                "total_max_marks": total_max_marks,
                "percentage": round(overall_percentage, 2),
                "grade": overall_grade,
                "total_subjects": len(exam_results),
                "pass_subjects": len([res for res in exam_results if float(res.marks_obtained) >= float(res.exam_subject.pass_marks)]),
            },
            "grading_system": [
                {"grade": "A+", "range": "90-100%", "remarks": "Outstanding"},
                {"grade": "A", "range": "80-89%", "remarks": "Excellent"},
                {"grade": "B+", "range": "70-79%", "remarks": "Very Good"},
                {"grade": "B", "range": "60-69%", "remarks": "Good"},
                {"grade": "C", "range": "50-59%", "remarks": "Average"},
                {"grade": "D", "range": "40-49%", "remarks": "Below Average"},
                {"grade": "F", "range": "Below 40%", "remarks": "Fail"},
            ],
            "export_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    def export_csv(self, data, filename):
        buffer = StringIO()
        writer = csv.writer(buffer)
        
        # Header
        writer.writerow([data['organization']['name']])
        writer.writerow(["REPORT CARD"])
        writer.writerow([])
        
        # Student Info
        writer.writerow(["Student Information"])
        writer.writerow(["Name:", data['student']['name']])
        writer.writerow(["Admission No:", data['student']['admission_number']])
        writer.writerow(["Class:", data['student']['class']])
        writer.writerow(["Section:", data['student']['section']])
        writer.writerow(["Roll No:", data['student']['roll_number']])
        writer.writerow([])
        
        # Exam Info
        writer.writerow(["Exam Information"])
        writer.writerow(["Exam:", data['exam']['name']])
        writer.writerow(["Type:", data['exam']['type']])
        writer.writerow(["Academic Year:", data['exam']['academic_year']])
        writer.writerow([])
        
        # Subject-wise Marks
        writer.writerow(["Subject-wise Performance"])
        writer.writerow(["Subject", "Marks Obtained", "Max Marks", "Percentage", "Grade", "Status"])
        for subject in data['subjects']:
            writer.writerow([
                subject['name'],
                subject['marks_obtained'],
                subject['max_marks'],
                f"{subject['percentage']:.2f}%",
                subject['grade'],
                subject['status']
            ])
        writer.writerow([])
        
        # Overall Performance
        writer.writerow(["Overall Performance"])
        writer.writerow(["Total Marks:", data['overall']['total_obtained']])
        writer.writerow(["Max Marks:", data['overall']['total_max_marks']])
        writer.writerow(["Percentage:", f"{data['overall']['percentage']}%"])
        writer.writerow(["Overall Grade:", data['overall']['grade']])
        writer.writerow(["Pass Subjects:", f"{data['overall']['pass_subjects']}/{data['overall']['total_subjects']}"])
        writer.writerow([])
        writer.writerow(["Exported on:", data['export_date']])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, data, filename):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            # Main sheet
            ws = workbook.add_worksheet("Report Card")
            
            # Formats
            header_fmt = workbook.add_format({
                "bold": True, "bg_color": "#2E86AB", "font_color": "white", 
                "border": 1, "align": "center", "font_size": 14
            })
            title_fmt = workbook.add_format({"bold": True, "font_size": 12})
            data_fmt = workbook.add_format({"border": 1})
            center_fmt = workbook.add_format({"align": "center", "border": 1})
            bold_fmt = workbook.add_format({"bold": True, "border": 1})
            
            # Header
            ws.merge_range('A1:F1', data['organization']['name'], header_fmt)
            ws.merge_range('A2:F2', "REPORT CARD", header_fmt)
            
            # Student Info
            ws.write(3, 0, "Student Information", title_fmt)
            ws.write(4, 0, "Name:", bold_fmt)
            ws.write(4, 1, data['student']['name'], data_fmt)
            ws.write(5, 0, "Admission No:", bold_fmt)
            ws.write(5, 1, data['student']['admission_number'], data_fmt)
            ws.write(6, 0, "Class:", bold_fmt)
            ws.write(6, 1, data['student']['class'], data_fmt)
            ws.write(7, 0, "Section:", bold_fmt)
            ws.write(7, 1, data['student']['section'], data_fmt)
            
            # Subject Performance Table
            row = 9
            headers = ["Subject", "Marks Obtained", "Max Marks", "Percentage", "Grade", "Status"]
            for col, header in enumerate(headers):
                ws.write(row, col, header, header_fmt)
            
            row += 1
            for subject in data['subjects']:
                ws.write(row, 0, subject['name'], data_fmt)
                ws.write(row, 1, subject['marks_obtained'], center_fmt)
                ws.write(row, 2, subject['max_marks'], center_fmt)
                ws.write(row, 3, f"{subject['percentage']:.2f}%", center_fmt)
                ws.write(row, 4, subject['grade'], center_fmt)
                ws.write(row, 5, subject['status'], center_fmt)
                row += 1
            
            # Overall Performance
            row += 1
            ws.write(row, 0, "Overall Performance", title_fmt)
            row += 1
            ws.write(row, 0, "Total Marks:", bold_fmt)
            ws.write(row, 1, data['overall']['total_obtained'], data_fmt)
            row += 1
            ws.write(row, 0, "Percentage:", bold_fmt)
            ws.write(row, 1, f"{data['overall']['percentage']}%", data_fmt)
            row += 1
            ws.write(row, 0, "Overall Grade:", bold_fmt)
            ws.write(row, 1, data['overall']['grade'], data_fmt)

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(), 
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, data, filename):
        context = {
            "data": data,
            "title": "Report Card"
        }
        pdf = render_to_pdf("examination/export/report_card_pdf.html", context)
        if pdf:
            return export_pdf_response(pdf, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

    def export_html(self, data):
        context = {
            "data": data,
            "title": "Report Card"
        }
        html_content = render_to_string("examination/export/report_card_html.html", context)
        return HttpResponse(html_content)