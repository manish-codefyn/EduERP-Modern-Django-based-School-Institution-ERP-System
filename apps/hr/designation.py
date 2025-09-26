# views.py

# Standard library imports
import csv
from io import BytesIO, StringIO

# Django imports
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q, Count
import xlsxwriter
# App-specific imports
from apps.core.utils import get_user_institution
from apps.core.mixins import HRRequiredMixin
from utils.utils import render_to_pdf, export_pdf_response

# Models and Forms
from .models import Designation, Staff
from .forms import DesignationForm



class DesignationListView( HRRequiredMixin, ListView):
    model = Designation
    template_name = 'hr/designation/designation_list.html'
    context_object_name = 'designations'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        institution = get_user_institution(self.request.user)

        if institution:
            queryset = queryset.filter(institution=institution)

        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        # Filter by category
        category_filter = self.request.GET.get('category', '')
        if category_filter:
            queryset = queryset.filter(category=category_filter)

        # Filter by active status
        active_filter = self.request.GET.get('is_active', '')
        if active_filter:
            if active_filter == 'true':
                queryset = queryset.filter(is_active=True)
            elif active_filter == 'false':
                queryset = queryset.filter(is_active=False)

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)

        # Filters for search & dropdowns
        context['search_query'] = self.request.GET.get('search', '')
        context['category_filter'] = self.request.GET.get('category', '')
        context['active_filter'] = self.request.GET.get('is_active', '')
        context['categories'] = dict(Designation.CATEGORY_CHOICES)

        # Stats Cards Data
        if institution:
            all_designations = Designation.objects.filter(institution=institution)
            context['total_designations'] = all_designations.count()
            context['active_designations'] = all_designations.filter(is_active=True).count()
            context['total_staff'] = Staff.objects.filter(designation__in=all_designations).count()
            
            # Count designations that have at least one staff marked as head
            context['designation_heads'] = Staff.objects.filter(reporting_manager__isnull=True, designation__in=all_designations).count()
        else:
            context['total_designations'] = 0
            context['active_designations'] = 0
            context['total_staff'] = 0
            context['designation_heads'] = 0
            
        return context
    
    
class DesignationCreateView( HRRequiredMixin, CreateView):
    model = Designation
    form_class = DesignationForm
    template_name = 'hr/designation/designation_form.html'
    success_url = reverse_lazy('hr:designation_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        
        # Get institution and pass it to the form
        institution = get_user_institution(self.request.user)
        if institution:
            kwargs['institution'] = institution
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Designation'
        context['submit_text'] = 'Create Designation'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Designation created successfully!')
        return super().form_valid(form)

class DesignationDetailView( HRRequiredMixin, DetailView):
    model = Designation
    template_name = 'hr/designation/designation_detail.html'
    context_object_name = 'designation'

class DesignationUpdateView( HRRequiredMixin, UpdateView):
    model = Designation
    form_class = DesignationForm
    template_name = 'hr/designation/designation_form.html'
    success_url = reverse_lazy('hr:designation_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        
        # Get institution and pass it to the form
        institution = get_user_institution(self.request.user)
        if institution:
            kwargs['institution'] = institution
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Designation'
        context['submit_text'] = 'Update Designation'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Designation updated successfully!')
        return super().form_valid(form)

class DesignationDeleteView( HRRequiredMixin, DeleteView):
    model = Designation
    template_name = 'hr/designation/designation_confirm_delete.html'
    success_url = reverse_lazy('hr:designation_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Designation deleted successfully!')
        return super().delete(request, *args, **kwargs)



class DesignationExportView( HRRequiredMixin, View):
    """
    Export Designation data in CSV, PDF, and Excel formats
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        category = request.GET.get("category")
        is_active = request.GET.get("is_active")

        institution = get_user_institution(request.user)
        qs = Designation.objects.filter(institution=institution).select_related('institution')

        if category:
            qs = qs.filter(category=category)
        if is_active:
            if is_active.lower() == 'true':
                qs = qs.filter(is_active=True)
            elif is_active.lower() == 'false':
                qs = qs.filter(is_active=False)

        qs = qs.order_by("name")

        filename_parts = ["designations"]
        if category:
            filename_parts.append(f"category_{category}")
        if is_active:
            filename_parts.append(f"active_{is_active}")
        filename = "_".join(filename_parts).lower()

        rows = []
        for designation in qs:
            # Count staff assigned to this designation
            total_staff = Staff.objects.filter(designation=designation).count()
            # Count designation head (assuming head field exists)
            designation_head = getattr(designation, 'head', None)
            rows.append({
                "name": designation.name,
                "code": designation.code,
                "category": designation.get_category_display(),
                "grade": designation.get_grade_display() if designation.grade else "N/A",
                "description": designation.description or "",
                "min_salary": designation.min_salary or "",
                "max_salary": designation.max_salary or "",
                "status": "Active" if designation.is_active else "Inactive",
                "total_staff": total_staff,
                "designation_head": designation_head.user.get_full_name() if designation_head else "Not Assigned",
                "created_at": designation.created_at.strftime("%Y-%m-%d %H:%M"),
                "updated_at": designation.updated_at.strftime("%Y-%m-%d %H:%M"),
            })

        organization = institution

        if fmt == "csv":
            return self.export_csv(rows, filename, organization)
        elif fmt == "pdf":
            return self.export_pdf(rows, filename, organization, qs.count())
        elif fmt == "excel":
            return self.export_excel(rows, filename, organization)

        return HttpResponse("Invalid format. Use csv, pdf, excel.", status=400)

    def export_csv(self, rows, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        headers = [
            "Name", "Code", "Category", "Grade", "Description",
            "Min Salary", "Max Salary", "Status",
            "Total Staff", "Designation Head",
            "Created At", "Updated At"
        ]
        writer.writerow(headers)

        for r in rows:
            writer.writerow([
                r['name'], r['code'], r['category'], r['grade'], r['description'],
                r['min_salary'], r['max_salary'], r['status'],
                r['total_staff'], r['designation_head'],
                r['created_at'], r['updated_at']
            ])

        # Summary
        writer.writerow([])
        writer.writerow(["Total Designations:", len(rows)])
        writer.writerow(["Organization:", organization.name if organization else "N/A"])
        writer.writerow(["Export Date:", timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_pdf(self, rows, filename, organization, total_count):
        context = {
            "designations": rows,
            "total_count": total_count,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and hasattr(organization, 'logo') else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and hasattr(organization, 'stamp') else None,
            "title": "Designations Export",
            "columns": [
                {"name": "Name", "width": "15%"},
                {"name": "Code", "width": "10%"},
                {"name": "Category", "width": "20%"},
                {"name": "Grade", "width": "20%"},
                {"name": "Total Staff", "width": "10%"},
                {"name": "Designation Head", "width": "15%"},
                {"name": "Status", "width": "10%"},
            ]
        }

        pdf_bytes = render_to_pdf("hr/export/designations_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            ws = workbook.add_worksheet("Designations")

            header_fmt = workbook.add_format({"bold": True, "bg_color": "#3b5998", "font_color": "white"})
            headers = [
                "Name", "Code", "Category", "Grade", "Description",
                "Min Salary", "Max Salary", "Status",
                "Total Staff", "Designation Head",
                "Created At", "Updated At"
            ]
            for col, h in enumerate(headers):
                ws.write(0, col, h, header_fmt)

            for i, r in enumerate(rows, start=1):
                ws.write(i, 0, r['name'])
                ws.write(i, 1, r['code'])
                ws.write(i, 2, r['category'])
                ws.write(i, 3, r['grade'])
                ws.write(i, 4, r['description'])
                ws.write(i, 5, r['min_salary'])
                ws.write(i, 6, r['max_salary'])
                ws.write(i, 7, r['status'])
                ws.write(i, 8, r['total_staff'])
                ws.write(i, 9, r['designation_head'])
                ws.write(i, 10, r['created_at'])
                ws.write(i, 11, r['updated_at'])

            # Adjust column widths
            ws.set_column("A:A", 20)
            ws.set_column("B:B", 10)
            ws.set_column("C:C", 15)
            ws.set_column("D:D", 15)
            ws.set_column("E:E", 30)
            ws.set_column("J:J", 20)

            summary_row = len(rows) + 2
            ws.write(summary_row, 0, "Total Designations:")
            ws.write(summary_row, 1, len(rows))
            ws.write(summary_row + 1, 0, "Organization:")
            ws.write(summary_row + 1, 1, organization.name if organization else "N/A")
            ws.write(summary_row + 2, 0, "Export Date:")
            ws.write(summary_row + 2, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response
