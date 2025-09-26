from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
import csv
from io import StringIO
from .models import AcademicYear
from apps.organization.models import Institution
from utils.utils import render_to_pdf, export_pdf_response
from .forms import AcademicYearForm  


class AcademicYearBaseView:
    """Base class for AcademicYear views"""

    def get_institution(self):
        user = self.request.user
        if hasattr(user, 'profile') and hasattr(user.profile, 'institution'):
            return user.profile.institution
        return None


# ===== LIST =====
class AcademicYearListView(AcademicYearBaseView, ListView):
    model = AcademicYear
    template_name = 'academics/academic_year/academic_year_list.html'
    context_object_name = 'academic_years'

    def get_queryset(self):
        institution = self.get_institution()
        if institution:
            return AcademicYear.objects.filter(institution=institution).order_by('-start_date')
        return AcademicYear.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = self.get_institution()
        if institution:
            all_years = AcademicYear.objects.filter(institution=institution)
            context['total_academic_years'] = all_years.count()
            context['current_academic_year'] = all_years.filter(is_current=True).first()
        else:
            context['total_academic_years'] = 0
            context['current_academic_year'] = None
        return context
    
# ===== CREATE =====


class AcademicYearCreateView(AcademicYearBaseView, CreateView):
    model = AcademicYear
    form_class = AcademicYearForm  # use the form class
    template_name = 'academics/academic_year/academic_year_form.html'
    success_url = reverse_lazy('academics:academic_year_list')

    def form_valid(self, form):
        # set the institution from the base view
        form.instance.institution = self.get_institution()
        response = super().form_valid(form)
        messages.success(self.request, f'Academic Year "{form.instance.name}" created successfully!')
        return response


class AcademicYearUpdateView(AcademicYearBaseView, UpdateView):
    model = AcademicYear
    form_class = AcademicYearForm  # use the form class
    template_name = 'academics/academic_year/academic_year_form.html'
    success_url = reverse_lazy('academics:academic_year_list')

    def get_queryset(self):
        # restrict to the current user's institution
        return AcademicYear.objects.filter(institution=self.get_institution())

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Academic Year "{form.instance.name}" updated successfully!')
        return response


# ===== DELETE =====
class AcademicYearDeleteView(AcademicYearBaseView, DeleteView):
    model = AcademicYear
    template_name = 'academics/academic_year/academic_year_confirm_delete.html'
    success_url = reverse_lazy('academics:academic_year_list')

    def get_queryset(self):
        return AcademicYear.objects.filter(institution=self.get_institution())

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Academic Year deleted successfully!')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verbose_name'] = self.model._meta.verbose_name
        return context


# ===== EXPORT =====
def export_academic_years(request):
    fmt = request.GET.get("format", "csv").lower()
    columns = request.GET.getlist("columns") or ["name", "start_date", "end_date", "is_current"]

    institution = None
    if hasattr(request.user, 'profile') and hasattr(request.user.profile, 'institution'):
        institution = request.user.profile.institution

    academic_years_qs = AcademicYear.objects.filter(institution=institution).order_by('-start_date') if institution else []

    rows = []
    for ay in academic_years_qs:
        r = {}
        if "name" in columns:
            r["name"] = ay.name
        if "start_date" in columns:
            r["start_date"] = ay.start_date.strftime("%b %d, %Y") if ay.start_date else ""
        if "end_date" in columns:
            r["end_date"] = ay.end_date.strftime("%b %d, %Y") if ay.end_date else ""
        if "is_current" in columns:
            r["is_current"] = "Yes" if ay.is_current else "No"
        rows.append(r)

    if fmt == "csv":
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow([col.replace("_", " ").title() for col in columns])
        for r in rows:
            writer.writerow([r.get(col, "") for col in columns])
        resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="academic_years.csv"'
        return resp

    if fmt == "pdf":
        organization = Institution.objects.first()
        context = {
            "columns": columns,
            "academic_years": rows,
            "generated_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization else None,
        }
        pdf_bytes = render_to_pdf("academics/academic_year/export_academic_years_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, "academic_years.pdf")
        return HttpResponse("Error generating PDF", status=500)

    return HttpResponse("Invalid export format", status=400)
