
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
from .models import Timetable,Class,AcademicYear,Section
from apps.organization.models import Institution
from utils.utils import render_to_pdf, export_pdf_response
from io import StringIO
from .forms import TimetableForm
from .views import AcademicsBaseView


def export_timetable(request, class_id=None):
    """
    Export Timetable as CSV or PDF, filtered by class and section if specified.
    GET params:
      - format: 'csv' or 'pdf' (default 'csv')
      - academic_year_id: UUID of the academic year to filter by
      - section_id: UUID of the section to filter by
      - columns: multiple columns via ?columns=day&columns=period
    """
    fmt = request.GET.get("format", "csv").lower()
    academic_year_id = request.GET.get("academic_year_id")
    section_id = request.GET.get("section_id")

    # Override class_id from querystring if needed
    if not class_id:
        class_id = request.GET.get("class_id")

    # Collect columns
    columns = request.GET.getlist("columns")
    if not columns:
        columns_param = request.GET.get("columns", "")
        if columns_param:
            columns = [c.strip() for c in columns_param.split(",") if c.strip()]

    # Default fields
    if not columns:
        columns = [
            "day", "period", "class_name", "section", "subject", "teacher",
            "start_time", "end_time", "room", "is_active",
        ]

    # Base queryset
    timetable_qs = Timetable.objects.all().order_by("day", "period")

    class_obj, section_obj, academic_year = None, None, None

    if class_id:
        timetable_qs = timetable_qs.filter(class_name_id=class_id)
        try:
            class_obj = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            class_obj = None

    if section_id:
        timetable_qs = timetable_qs.filter(section_id=section_id)
        try:
            section_obj = Section.objects.get(id=section_id)
        except Section.DoesNotExist:
            section_obj = None

    if academic_year_id:
        timetable_qs = timetable_qs.filter(academic_year=academic_year_id)
        try:
            academic_year = AcademicYear.objects.get(id=academic_year_id)
        except AcademicYear.DoesNotExist:
            academic_year = None

    # Filename
    filter_details = []
    if class_obj:
        filter_details.append(f"Class_{class_obj.name}")
    if section_obj:
        filter_details.append(f"Section_{section_obj.name}")
    if academic_year:
        filter_details.append(f"Year_{academic_year.name}")

    filename = "timetable"
    if filter_details:
        filename = f"timetable_{'_'.join(filter_details)}"

    # Build rows
    rows = []
    for timetable in timetable_qs:
        r = {}
        if "day" in columns:
            r["day"] = timetable.get_day_display()
        if "period" in columns:
            r["period"] = timetable.period
        if "class_name" in columns:
            r["class_name"] = str(timetable.class_name)
        if "section" in columns:
            r["section"] = str(timetable.section)
        if "subject" in columns:
            r["subject"] = str(timetable.subject)
        if "teacher" in columns:
            r["teacher"] = str(timetable.teacher.get_full_name())
        if "start_time" in columns:
            r["start_time"] = timetable.start_time.strftime("%H:%M") if timetable.start_time else ""
        if "end_time" in columns:
            r["end_time"] = timetable.end_time.strftime("%H:%M") if timetable.end_time else ""
        if "room" in columns:
            r["room"] = timetable.room
        if "is_active" in columns:
            r["is_active"] = "Active" if timetable.is_active else "Inactive"
        rows.append(r)

    # === CSV Export ===
    if fmt == "csv":
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow([col.replace("_", " ").title() for col in columns])
        for r in rows:
            writer.writerow([r.get(col, "") for col in columns])

        resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return resp

    # === PDF Export ===
    if fmt == "pdf":
        organization = Institution.objects.first()

        # Group class-wise timetables
        class_data = []
        if class_obj:
            class_rows = [r for r in rows if r.get("class_name") == str(class_obj)]
            class_data.append({
                "class": class_obj,
                "section": section_obj,
                "entries": class_rows
            })
        else:
            for c in Class.objects.all().order_by("name"):
                class_rows = [r for r in rows if r.get("class_name") == str(c)]
                if class_rows:
                    class_data.append({"class": c, "section": None, "entries": class_rows})
        # Filter columns for PDF table (remove class_name, section, is_active)
        filtered_columns = [c for c in columns if c not in ('class_name', 'section', 'is_active')]

        context = {
            "columns": columns,
            "filtered_columns": filtered_columns,
            "class_data": class_data,
            "generated_date": timezone.now(),
            "organization": organization,
            "academic_year": academic_year,
            "logo": getattr(organization.logo, "url", None) if organization else None,
            "stamp": getattr(organization.stamp, "url", None) if organization else None,
        }

        pdf_bytes = render_to_pdf("academics/timetable/export_timetable_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

    return HttpResponse("Invalid export format", status=400)



# ===== TIMETABLE VIEWS =====
class TimetableView(AcademicsBaseView, ListView):
    model = Timetable
    template_name = 'academics/timetable/timetable_list.html'
    context_object_name = 'timetable_entries'
        
    def get_queryset(self):
        class_id = self.kwargs['class_id']
        institution = self.get_institution()
        
        # Get current academic year
        current_year = self.get_current_academic_year()
        
        return Timetable.objects.filter(
            class_name_id=class_id,
            institution=institution,
            academic_year=current_year
        ).select_related('subject', 'teacher', 'section').order_by('day', 'period')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs['class_id']
        institution = self.get_institution()
        
        # Class object
        context['class_obj'] = get_object_or_404(Class, id=class_id, institution=institution)
        
        # Days & periods
        context['days'] = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        context['periods'] = range(1, 9)
        
        # Current & all academic years
        current_year = self.get_current_academic_year()
        context['current_year'] = current_year
        context['academic_year'] = current_year
        context['academic_years'] = AcademicYear.objects.filter(
            institution=institution
        ).order_by('-start_date')
        

        
        # Fields available for export checkboxes
        context['class_fields'] = ['day', 'period', 'subject', 'teacher', 'section']
        
        return context



class TimetableCreateView(AcademicsBaseView, CreateView):
    model = Timetable
    form_class = TimetableForm
    template_name = 'academics/timetable/timetable_form.html'
    success_url = reverse_lazy('academics:class_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['institution'] = self.get_institution()
        return kwargs
    
    def form_valid(self, form):
        form.instance.institution = self.get_institution()
        response = super().form_valid(form)
        messages.success(self.request, 'Timetable entry created successfully!')
        return response


class TimetableUpdateView(AcademicsBaseView, UpdateView):
    model = Timetable
    form_class = TimetableForm
    template_name = 'academics/timetable/timetable_form.html'
        
    def get_queryset(self):
        return Timetable.objects.filter(institution=self.get_institution())
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['institution'] = self.get_institution()
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Timetable entry updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse('academics:timetable_list', kwargs={'class_id': self.object.class_name.id})



class TimetableDeleteView(AcademicsBaseView, DeleteView):
    model = Timetable
    template_name = 'academics/timetable/timetable_confirm_delete.html'
      
    def get_queryset(self):
        return Timetable.objects.filter(institution=self.get_institution())
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Timetable entry deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('academics:class_timetable', kwargs={'class_id': self.object.class_name.id})