from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import timedelta
import csv
import csv
from io import StringIO
from .models import Class, Section, Subject, AcademicYear, Timetable
from .forms import ClassForm, SectionForm, TimetableForm
from django.utils import timezone
from django.conf import settings
import os
from .models import Class, Section, Timetable, AcademicYear
from apps.organization.models import Institution
from utils.utils import render_to_pdf, export_pdf_response


class AcademicsBaseView:
    """Base class for academics views with common methods"""
    
    def get_institution(self):
        """Get institution from the logged-in user's profile."""
        user = self.request.user
        if hasattr(user, 'profile') and hasattr(user.profile, 'institution'):
            return user.profile.institution
        return None
    
    def get_current_academic_year(self):
        """Get current academic year for the institution."""
        institution = self.get_institution()
        if institution:
            try:
                return AcademicYear.objects.filter(
                    is_current=True, 
                    institution=institution
                ).first()
            except AcademicYear.DoesNotExist:
                return None
        return None


def export_classes(request):
    """Export Classes as CSV, Excel, or PDF"""
    export_format = request.GET.get("format", "csv")
    include_sections = request.GET.get("includeSections", "true") == "true"
    include_capacity = request.GET.get("includeCapacity", "true") == "true"

    classes = Class.objects.prefetch_related("sections").all()

    # Build data rows
    data = []
    for c in classes:
        row = {
            "name": c.name,
            "code": c.code,
        }
        if include_capacity:
            row["capacity"] = c.capacity
        if include_sections:
            row["sections"] = ", ".join([s.name for s in c.sections.all()])
        
        # Add Room Number
        row["room_number"] = c.room_number if c.room_number else "Not Assigned"
        
        data.append(row)

    # CSV
    if export_format == "csv":
        import csv
        from io import StringIO

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="classes.csv"'

        writer = csv.DictWriter(response, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return response

    # Excel
    elif export_format == "excel":
        import pandas as pd
        from io import BytesIO

        df = pd.DataFrame(data)
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="classes.xlsx"'

        with BytesIO() as buffer:
            df.to_excel(buffer, index=False)
            response.write(buffer.getvalue())
        return response

    # PDF using xhtml2pdf
    elif export_format == "pdf":
        organization = Institution.objects.first()
        context = {
            "classes": data,
            "include_capacity": include_capacity,
            "include_sections": include_sections,
            # Add logo & stamp paths (MEDIA or STATIC)
            "logo": getattr(organization.logo, 'url', None) if organization else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization else None,
        }
        pdf_bytes = render_to_pdf("academics/classes_list_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, "classes.pdf")
        return HttpResponse("Error generating PDF", status=500)

    else:
        return HttpResponse("Invalid format", status=400)


class ClassReportPDFView(AcademicsBaseView, View):
    def get(self, request, pk):
        institution = self.get_institution()
        class_obj = get_object_or_404(Class, pk=pk, institution=institution)
        sections = Section.objects.filter(class_name=class_obj, is_active=True)
        timetable_entries = Timetable.objects.filter(class_name=class_obj, is_active=True)
        current_year = self.get_current_academic_year()
        organization = Institution.objects.first()
        days = ["monday", "tuesday", "wednesday", "thursday", "friday"]

        context = {
            "class_obj": class_obj,
            "sections": sections,
            "timetable_entries": timetable_entries,
            "current_year": current_year,
            "Institution": organization,
            "days": days,
            "generated_date": timezone.now(),
            # Add logo & stamp paths (MEDIA or STATIC)
            "logo": getattr(organization.logo, 'url', None) if organization else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization else None,
        }

        pdf = render_to_pdf("academics/class_report_pdf.html", context)
        if pdf:
            return export_pdf_response(pdf, f"class_report_{class_obj.code}.pdf")
        return HttpResponse("Error generating PDF", status=500)


# ===== SECTION VIEWS =====


def export_sections(request):
    """
    Export Sections as CSV or PDF.
    GET params:
      - format: 'csv' or 'pdf' (default 'csv')
      - columns: multiple columns via ?columns=name&columns=capacity (or single csv string)
    """
    fmt = request.GET.get("format", "csv").lower()
    
    # Accept multiple columns
    columns = request.GET.getlist("columns")
    if not columns:
        columns_param = request.GET.get("columns", "")
        if columns_param:
            columns = [c.strip() for c in columns_param.split(",") if c.strip()]

    # Default columns if none selected
    if not columns:
        columns = ["class_name", "name", "capacity", "is_active", "created_at"]

    sections_qs = Section.objects.select_related("class_name").all().order_by("class_name__name", "name")

    # Prepare rows
    rows = []
    for s in sections_qs:
        r = {}
        if "class_name" in columns:
            r["class_name"] = s.class_name.name
        if "name" in columns:
            r["name"] = s.name
        if "capacity" in columns:
            r["capacity"] = s.capacity
        if "is_active" in columns:
            r["is_active"] = "Active" if s.is_active else "Inactive"
        if "created_at" in columns:
            r["created_at"] = s.created_at.strftime("%b %d, %Y") if s.created_at else ""
        rows.append(r)

    # CSV Export
    if fmt == "csv":
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow([col.replace("_", " ").title() for col in columns])  # header
        for r in rows:
            writer.writerow([r.get(col, "") for col in columns])
        resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="sections.csv"'
        return resp

    # PDF Export
    if fmt == "pdf":
        organization = Institution.objects.first()
        context = {
            "columns": columns,
            "sections": rows,
            "generated_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, "url", None) if organization else None,
            "stamp": getattr(organization.stamp, "url", None) if organization else None,
        }
        pdf_bytes = render_to_pdf("academics/section/export_sections_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, "sections.pdf")
        return HttpResponse("Error generating PDF", status=500)

    return HttpResponse("Invalid export format", status=400)


class SectionListView(AcademicsBaseView, ListView):
    model = Section
    template_name = 'academics/section/section_list.html'
    context_object_name = 'sections'

    def get_queryset(self):
        class_id = self.kwargs.get('class_id')
        institution = self.get_institution()
        return Section.objects.filter(
            class_name_id=class_id,
            institution=institution
        ).select_related('class_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs.get('class_id')
        institution = self.get_institution()
        class_obj = get_object_or_404(Class, id=class_id, institution=institution)

        sections_qs = Section.objects.filter(class_name=class_obj, institution=institution)

        total_sections = sections_qs.count()
        active_sections = sections_qs.filter(is_active=True).count()
        inactive_sections = sections_qs.filter(is_active=False).count()

        total_capacity = sections_qs.aggregate(total=Sum('capacity'))['total'] or 0
        avg_capacity = round(total_capacity / total_sections, 2) if total_sections else 0

        # Only concrete fields
        field_names = [f.name for f in Section._meta.get_fields() if f.concrete and not f.many_to_many]

        context.update({
            'class_obj': class_obj,
            'total_sections': total_sections,
            'active_sections': active_sections,
            'inactive_sections': inactive_sections,
            'total_capacity': total_capacity,
            'avg_capacity': avg_capacity,
            'section_fields': field_names,
        })
        return context

class SectionCreateView(AcademicsBaseView, CreateView):
    model = Section
    form_class = SectionForm
    template_name = 'academics/section/section_form.html'
    
    def get_initial(self):
        class_id = self.kwargs['class_id']
        return {'class_name': class_id}
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['institution'] = self.get_institution()
        return kwargs
    
    def form_valid(self, form):
        form.instance.institution = self.get_institution()
        form.instance.class_name_id = self.kwargs['class_id']
        response = super().form_valid(form)
        messages.success(self.request, f'Section "{form.instance.name}" created successfully!')
        return response
    
    def get_success_url(self):
        return reverse('academics:section_list', kwargs={'class_id': self.kwargs['class_id']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_obj = get_object_or_404(Class, pk=self.kwargs['class_id'])
        context['class_obj'] = class_obj  
        context['class_id'] = self.kwargs['class_id']
        return context


class SectionUpdateView(AcademicsBaseView, UpdateView):
    model = Section
    form_class = SectionForm
    template_name = 'academics/section/section_form.html'

    def get_queryset(self):
        """Restrict sections to the current user's institution."""
        institution = self.get_institution()
        if institution:
            return Section.objects.filter(institution=institution)
        return Section.objects.none()

    def get_form_kwargs(self):
        """Pass institution to form for filtering related fields."""
        kwargs = super().get_form_kwargs()
        kwargs['institution'] = self.get_institution()
        return kwargs

    def form_valid(self, form):
        """Add success message after update."""
        response = super().form_valid(form)
        messages.success(self.request, f'Section "{form.instance.name}" updated successfully!')
        return response

    def get_success_url(self):
        """Redirect back to the section list of the class."""
        return reverse('academics:section_list', kwargs={'class_id': self.object.class_name.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        section = self.object
        class_obj = section.class_name
        context['class_obj'] = class_obj
        context['class_id'] = class_obj.id
        return context


class SectionDeleteView(AcademicsBaseView, DeleteView):
    model = Section
    template_name = 'academics/section/section_confirm_delete.html'
        
    def get_queryset(self):
        return Section.objects.filter(institution=self.get_institution())
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Section deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('academics:section_list', kwargs={'class_id': self.object.class_name.id})


# ===== REPORT VIEWS =====
class ClassReportView(AcademicsBaseView, TemplateView):
    template_name = 'academics/class_report.html'
                
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs['class_id']
        institution = self.get_institution()
        
        class_obj = get_object_or_404(Class, id=class_id, institution=institution)
        sections = Section.objects.filter(class_name=class_obj, institution=institution)
        
        # Get timetable data
        current_year = self.get_current_academic_year()
        timetable_entries = Timetable.objects.filter(
            class_name=class_obj,
            institution=institution,
            academic_year=current_year
        )
        
        context['class_obj'] = class_obj
        context['sections'] = sections
        context['timetable_entries'] = timetable_entries
        context['current_year'] = current_year
        context['generated_date'] = timezone.now()
        
        return context


class ClassSummaryReportView(AcademicsBaseView, TemplateView):
    template_name = 'academics/class_summary_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = self.get_institution()
        
        classes = Class.objects.filter(institution=institution).annotate(
            section_count=Count('sections'),
            total_capacity=Sum('capacity')
        )
        
        context['classes'] = classes
        context['total_classes'] = classes.count()
        context['total_sections'] = Section.objects.filter(institution=institution).count()
        context['overall_capacity'] = classes.aggregate(Sum('capacity'))['capacity__sum'] or 0
        context['average_capacity'] = classes.aggregate(Avg('capacity'))['capacity__avg'] or 0
        context['generated_date'] = timezone.now()
        
        return context


class ClassListView(AcademicsBaseView, ListView):
    model = Class
    template_name = 'academics/class_list.html'
    context_object_name = 'object_list'
    
    def get_queryset(self):
        institution = self.get_institution()
        if institution:
            return Class.objects.filter(institution=institution).prefetch_related('sections')
        return Class.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = self.get_institution()
        
        if institution:
            classes = Class.objects.filter(institution=institution)
            context['active_classes_count'] = classes.filter(is_active=True).count()
            context['total_sections'] = Section.objects.filter(institution=institution).count()
            context['total_capacity'] = classes.aggregate(Sum('capacity'))['capacity__sum'] or 0
            context['average_capacity'] = round(classes.aggregate(Avg('capacity'))['capacity__avg'] or 0, 1)
            context['first_class'] = Class.objects.first()
        else:
            context['active_classes_count'] = 0
            context['total_sections'] = 0
            context['total_capacity'] = 0
            context['average_capacity'] = 0
            context['first_class'] = Class.objects.first()
            
        return context


class ClassDeleteView(AcademicsBaseView, DeleteView):
    model = Class
    template_name = 'academics/class_confirm_delete.html'
    success_url = reverse_lazy('academics:class_list')

    def get_queryset(self):
        """Restrict deletion to classes of the user's institution"""
        institution = self.get_institution()
        if institution:
            return Class.objects.filter(institution=institution)
        return Class.objects.none()

    def delete(self, request, *args, **kwargs):
        """Add success message on deletion"""
        obj = self.get_object()
        messages.success(request, f'Class "{obj.name}" was deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    
class ClassDetailView(AcademicsBaseView, DetailView):
    model = Class
    template_name = 'academics/class_detail.html'
    context_object_name = 'class_obj'

    def get_queryset(self):
        """Restrict access to classes belonging to the user's institution"""
        institution = self.get_institution()
        if institution:
            return Class.objects.filter(institution=institution)
        return Class.objects.none()


class ClassCreateView(AcademicsBaseView, CreateView):
    model = Class
    form_class = ClassForm
    template_name = 'academics/class_form.html'
    success_url = reverse_lazy('academics:class_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        institution = self.get_institution()
        if institution:
            kwargs['institution'] = institution
        return kwargs
    
    def form_valid(self, form):
        institution = self.get_institution()
        if institution:
            form.instance.institution = institution
            response = super().form_valid(form)
            messages.success(self.request, f'Class "{self.object.name}" was created successfully!')
            return response
        else:
            form.add_error(None, 'You must be associated with an institution to create a class.')
            return self.form_invalid(form)


class ClassUpdateView(AcademicsBaseView, UpdateView):
    model = Class
    form_class = ClassForm
    template_name = 'academics/class_form.html'
    success_url = reverse_lazy('academics:class_list')
    
    def get_queryset(self):
        institution = self.get_institution()
        if institution:
            return Class.objects.filter(institution=institution)
        return Class.objects.none()
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        institution = self.get_institution()
        if institution:
            kwargs['institution'] = institution
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Class "{self.object.name}" was updated successfully!')
        return response