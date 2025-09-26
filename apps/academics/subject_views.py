
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import csv
from django.conf import settings
from .models import Subject
from apps.organization.models import Institution
from utils.utils import render_to_pdf, export_pdf_response
from io import StringIO
from .forms import SubjectForm
from .views import AcademicsBaseView

def export_subjects(request):
    """
    Export Subjects as CSV or PDF.
    GET params:
      - format: 'csv' or 'pdf' (default 'csv')
      - columns: multiple columns via ?columns=name&columns=code
    """
    fmt = request.GET.get("format", "csv").lower()

    # Accept both repeated parameters and comma-separated style
    columns = request.GET.getlist("columns")
    if not columns:
        columns_param = request.GET.get("columns", "")
        if columns_param:
            columns = [c.strip() for c in columns_param.split(",") if c.strip()]

    # Default fields if none selected
    if not columns:
        columns = [
            "name", "code", "subject_type", "difficulty_level", "credits",
            "department", "prerequisites", "description", "is_active", "created_at"
        ]

    subjects_qs = Subject.objects.all().order_by("name")

    # Build rows as plain dicts and format values for easy template/csv usage
    rows = []
    for subject in subjects_qs:
        r = {}
        if "name" in columns:
            r["name"] = subject.name
        if "code" in columns:
            r["code"] = subject.code or ""
        if "subject_type" in columns:
            r["subject_type"] = subject.get_subject_type_display()
        if "difficulty_level" in columns:
            r["difficulty_level"] = subject.get_difficulty_level_display()
        if "credits" in columns:
            r["credits"] = subject.credits
        if "department" in columns:
            r["department"] = subject.department.name if subject.department else "-"
        if "prerequisites" in columns:
            r["prerequisites"] = ", ".join([p.name for p in subject.prerequisites.all()])
        if "description" in columns:
            r["description"] = (subject.description[:200] + "...") if subject.description else ""
        if "is_active" in columns:
            r["is_active"] = "Active" if subject.is_active else "Inactive"
        if "created_at" in columns:
            r["created_at"] = subject.created_at.strftime("%b %d, %Y") if subject.created_at else ""
        rows.append(r)

    # CSV export
    if fmt == "csv":
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow([col.replace("_", " ").title() for col in columns])
        for r in rows:
            writer.writerow([r.get(col, "") for col in columns])
        resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="subjects.csv"'
        return resp

    # PDF export
    if fmt == "pdf":
        organization = Institution.objects.first()
        context = {
            "columns": columns,
            "subjects": rows,
            "generated_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization else None,
        }

        pdf_bytes = render_to_pdf("academics/subject/export_subjects_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, "subjects.pdf")
        return HttpResponse("Error generating PDF", status=500)

    return HttpResponse("Invalid export format", status=400)



# ===== SUBJECT VIEWS =====
class SubjectListView(AcademicsBaseView, ListView):
    model = Subject
    template_name = 'academics/subject/subject_list.html'
    context_object_name = 'subjects'

    def get_queryset(self):
        institution = self.get_institution()
        if institution:
            return Subject.objects.filter(institution=institution).order_by('name')
        return Subject.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = self.get_institution()
        if institution:
            subjects = Subject.objects.filter(institution=institution)

            context['total_subjects'] = subjects.count()
            context['active_subjects_count'] = subjects.filter(is_active=True).count()
            context['core_subjects_count'] = subjects.filter(subject_type=Subject.CORE).count()
            context['elective_subjects_count'] = subjects.filter(subject_type=Subject.ELECTIVE).count()

        return context


class SubjectCreateView(AcademicsBaseView, CreateView):
    model = Subject
    form_class = SubjectForm
    template_name = 'academics/subject/subject_form.html'
    success_url = reverse_lazy('academics:subject_list')

    def form_valid(self, form):
        form.instance.institution = self.get_institution()
        response = super().form_valid(form)
        messages.success(self.request, f'Subject "{form.instance.name}" created successfully!')
        return response

    def form_invalid(self, form):
        messages.error(self.request, "There was an error creating the subject. Please check the form and try again.")
        return super().form_invalid(form)


class SubjectUpdateView(AcademicsBaseView, UpdateView):
    model = Subject
    form_class = SubjectForm
    template_name = 'academics/subject/subject_form.html'
    success_url = reverse_lazy('academics:subject_list')

    def get_queryset(self):
        # Ensure users can only update subjects in their institution
        return Subject.objects.filter(institution=self.get_institution())

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Subject "{form.instance.name}" updated successfully!')
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "There was an error updating the subject. Please check the form and try again."
        )
        return super().form_invalid(form)



class SubjectDeleteView(AcademicsBaseView, DeleteView):
    model = Subject
    template_name = 'academics/subject/subject_confirm_delete.html'
    success_url = reverse_lazy('academics:subject_list')

    def get_queryset(self):
        return Subject.objects.filter(institution=self.get_institution())

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Subject deleted successfully!')
        return super().delete(request, *args, **kwargs)
