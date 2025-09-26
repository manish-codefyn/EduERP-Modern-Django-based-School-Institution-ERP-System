from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q
from io import StringIO, BytesIO
import csv
import xlsxwriter
import uuid
from .models import Department
from .forms import DepartmentForm
from apps.core.utils import get_user_institution
from apps.core.mixins import HRRequiredMixin,DirectorRequiredMixin
from utils.utils import render_to_pdf, export_pdf_response


class DepartmentListView( HRRequiredMixin, ListView):
    model = Department
    template_name = 'hr/department/department_list.html'
    context_object_name = 'departments'
    paginate_by = 20
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = Department.objects.filter(institution=institution).select_related(
            'institution', 'head_of_department', 'head_of_department__user'
        ).order_by('name')
        
        # Filter by department type if provided
        department_type = self.request.GET.get('department_type')
        if department_type:
            queryset = queryset.filter(department_type=department_type)
        
        # Filter by active status if provided
        is_active = self.request.GET.get('is_active')
        if is_active:
            if is_active.lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() == 'false':
                queryset = queryset.filter(is_active=False)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search) |
                Q(head_of_department__user__first_name__icontains=search) |
                Q(head_of_department__user__last_name__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Statistics
        context['total_departments'] = Department.objects.filter(institution=institution).count()
        context['active_departments'] = Department.objects.filter(
            institution=institution, is_active=True
        ).count()
        context['inactive_departments'] = Department.objects.filter(
            institution=institution, is_active=False
        ).count()
        
        # Department type choices for filters
        context['department_type_choices'] = Department.DEPARTMENT_TYPE_CHOICES
        
        # Current filters
        context['current_department_type'] = self.request.GET.get('department_type', '')
        context['current_is_active'] = self.request.GET.get('is_active', '')
        context['current_search'] = self.request.GET.get('search', '')
        
        return context


class DepartmentCreateView( HRRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'hr/department/department_form.html'
    success_url = reverse_lazy('hr:department_list')
    
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
        context['title'] = 'Create Department'
        context['submit_text'] = 'Create Department'
        return context
    
    def form_valid(self, form):
        # The form's save method will handle institution assignment and code generation
        messages.success(self.request, 'Department created successfully!')
        return super().form_valid(form)

class DepartmentUpdateView( HRRequiredMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'hr/department/department_form.html'
    success_url = reverse_lazy('hr:department_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        
        # Pass institution to form
        if self.object and self.object.institution:
            kwargs['institution'] = self.object.institution
        else:
            # fallback if object has no institution
            institution = get_user_institution(self.request.user)
            if institution:
                kwargs['institution'] = institution
        
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Department'
        context['submit_text'] = 'Update Department'
        context['back_url'] = reverse_lazy('hr:department_list')
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Department updated successfully!')
        return super().form_valid(form)


class DepartmentDeleteView( HRRequiredMixin, DeleteView):
    model = Department
    template_name = 'hr/department/department_confirm_delete.html'
    success_url = reverse_lazy('hr:department_list')
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Department.objects.filter(institution=institution)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Department deleted successfully!')
        return super().delete(request, *args, **kwargs)


class DepartmentDetailView( HRRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        department = get_object_or_404(
            Department, 
            id=kwargs['pk'],
            institution=get_user_institution(request.user)
        )
        # You can render a detail template here or return JSON for API
        return redirect('hr:department_list')


class DepartmentToggleActiveView( HRRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        department = get_object_or_404(
            Department, 
            id=kwargs['pk'],
            institution=get_user_institution(request.user)
        )
        
        department.is_active = not department.is_active
        department.save()
        
        status = "activated" if department.is_active else "deactivated"
        messages.success(request, f'Department {status} successfully!')
        
        return redirect('hr:department_list')


class DepartmentExportView( HRRequiredMixin, View):
    """
    Export Department data in CSV, PDF, Excel formats
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        department_type = request.GET.get("department_type")
        is_active = request.GET.get("is_active")

        institution = get_user_institution(request.user)
        qs = Department.objects.filter(institution=institution).select_related(
            'institution', 'head_of_department', 'head_of_department__user'
        )

        if department_type:
            qs = qs.filter(department_type=department_type)
        if is_active:
            if is_active.lower() == 'true':
                qs = qs.filter(is_active=True)
            elif is_active.lower() == 'false':
                qs = qs.filter(is_active=False)

        qs = qs.order_by("name")

        filename_parts = ["departments"]
        if department_type:
            filename_parts.append(f"type_{department_type}")
        if is_active:
            filename_parts.append(f"active_{is_active}")
        filename = "_".join(filename_parts).lower()

        rows = []
        for department in qs:
            rows.append({
                "name": department.name,
                "code": department.code,
                "department_type": department.get_department_type_display(),
                "description": department.description,
                "head_of_department": department.head_of_department.user.get_full_name() if department.head_of_department else "Not Assigned",
                "email": department.email,
                "phone": department.phone,
                "office_location": department.office_location,
                "is_active": "Yes" if department.is_active else "No",
                "created_at": department.created_at.strftime("%Y-%m-%d %H:%M"),
                "updated_at": department.updated_at.strftime("%Y-%m-%d %H:%M"),
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

        writer.writerow([
            "Name", "Code", "Type", "Description", "Head of Department", 
            "Email", "Phone", "Office Location", "Active", 
            "Created At", "Updated At"
        ])

        for row in rows:
            writer.writerow([
                row["name"], row["code"], row["department_type"], row["description"], 
                row["head_of_department"], row["email"], row["phone"], 
                row["office_location"], row["is_active"], row["created_at"], 
                row["updated_at"]
            ])

        writer.writerow([])
        writer.writerow(["Total Departments:", len(rows)])
        writer.writerow(["Organization:", organization.name if organization else "N/A"])
        writer.writerow(["Export Date:", timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_pdf(self, rows, filename, organization, total_count):
        context = {
            "departments": rows,
            "total_count": total_count,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Departments Export",
            "columns": [
                {"name": "Name", "width": "15%"},
                {"name": "Code", "width": "10%"},
                {"name": "Type", "width": "15%"},
                {"name": "Head of Department", "width": "15%"},
                {"name": "Email", "width": "20%"},
                {"name": "Phone", "width": "15%"},
                {"name": "Active", "width": "10%"},
            ]
        }

        pdf_bytes = render_to_pdf("hr/export/departments_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            ws = workbook.add_worksheet("Departments")

            header_fmt = workbook.add_format({"bold": True, "bg_color": "#3b5998", "font_color": "white"})

            headers = [
                "Name", "Code", "Type", "Description", "Head of Department", 
                "Email", "Phone", "Office Location", "Active", 
                "Created At", "Updated At"
            ]

            for col, h in enumerate(headers):
                ws.write(0, col, h, header_fmt)

            for i, r in enumerate(rows, start=1):
                ws.write(i, 0, r['name'])
                ws.write(i, 1, r['code'])
                ws.write(i, 2, r['department_type'])
                ws.write(i, 3, r['description'])
                ws.write(i, 4, r['head_of_department'])
                ws.write(i, 5, r['email'])
                ws.write(i, 6, r['phone'])
                ws.write(i, 7, r['office_location'])
                ws.write(i, 8, r['is_active'])
                ws.write(i, 9, r['created_at'])
                ws.write(i, 10, r['updated_at'])

            ws.set_column("A:K", 15)
            ws.set_column("D:D", 25)  # Wider column for description
            ws.set_column("E:E", 20)  # Wider column for head of department

            summary_row = len(rows) + 2
            ws.write(summary_row, 0, "Total Departments:")
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