import csv
from io import StringIO, BytesIO
from datetime import datetime
import xlsxwriter
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import StaffManagementRequiredMixin
from .models import Institution, Department, Branch, InstitutionCompliance
from .forms import (InstitutionForm, DepartmentForm, BranchForm, 
   InstitutionFilterForm
)
from apps.core.utils import get_user_institution
import json


class OrganizationDashboardView( StaffManagementRequiredMixin, TemplateView):
    template_name = 'organization/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Basic statistics (No change here)
        total_institutions = Institution.objects.count()
        active_institutions = Institution.objects.filter(is_active=True).count()
        
        # ## MODIFICATION FOR CHARTS ##
        # Get the choices from the model to map keys to display names
        type_choices = dict(Institution.TYPE_CHOICES) # Assumes your model has TYPE_CHOICES

        # Type breakdown query (No change here)
        type_stats_query = Institution.objects.values('type').annotate(count=Count('id')).order_by('-count')
        
        # Prepare the data for Chart.js
        type_chart_data = {
            'labels': json.dumps([type_choices.get(item['type'], item['type']) for item in type_stats_query]),
            'data': json.dumps([item['count'] for item in type_stats_query])
        }
        # ## END MODIFICATION ##

        # Recent institutions (No change here)
        recent_institutions = Institution.objects.all().order_by('-created_at')[:5]
        
        # Department and branch statistics (No change here)
        department_stats = Department.objects.filter(institution=institution).aggregate(
            total_departments=Count('id'),
            active_departments=Count('id', filter=Q(is_active=True))
        )
        
        branch_stats = Branch.objects.filter(institution=institution).aggregate(
            total_branches=Count('id'),
            active_branches=Count('id', filter=Q(is_active=True))
        )
        
        # Compliance status (No change here)
        compliance_stats = {
            'with_gst': InstitutionCompliance.objects.filter(gst_number__isnull=False).count(),
            'with_pan': InstitutionCompliance.objects.filter(pan_number__isnull=False).count(),
        }
        
        context.update({
            'total_institutions': total_institutions,
            'active_institutions': active_institutions,
            # 'type_stats': type_stats, # We no longer need to pass the raw stats
            'type_chart_data': type_chart_data, # Pass the prepared chart data instead
            'recent_institutions': recent_institutions,
            'total_departments': department_stats['total_departments'] or 0,
            'active_departments': department_stats['active_departments'] or 0,
            'total_branches': branch_stats['total_branches'] or 0,
            'active_branches': branch_stats['active_branches'] or 0,
            'compliance_stats': compliance_stats,
        })
        return context

# Institution CRUD Views
class InstitutionListView( StaffManagementRequiredMixin, ListView):
    model = Institution
    template_name = 'organization/institution/institution_list.html'
    context_object_name = 'institutions'
    paginate_by = 20

    def get_queryset(self):
        queryset = Institution.objects.all()
        
        # Apply filters
        form = InstitutionFilterForm(self.request.GET)
        if form.is_valid():
            type_filter = form.cleaned_data.get('type')
            country_filter = form.cleaned_data.get('country')
            is_active_filter = form.cleaned_data.get('is_active')
            search_filter = form.cleaned_data.get('search')
            
            if type_filter:
                queryset = queryset.filter(type=type_filter)
            if country_filter:
                queryset = queryset.filter(country__icontains=country_filter)
            if is_active_filter:
                if is_active_filter == 'true':
                    queryset = queryset.filter(is_active=True)
                elif is_active_filter == 'false':
                    queryset = queryset.filter(is_active=False)
            if search_filter:
                queryset = queryset.filter(
                    Q(name__icontains=search_filter) |
                    Q(code__icontains=search_filter) |
                    Q(short_name__icontains=search_filter)
                )
        
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = InstitutionFilterForm(self.request.GET)
        context['total_institutions'] = self.get_queryset().count()
        context['active_institutions'] = self.get_queryset().filter(is_active=True).count()
        return context


class InstitutionCreateView( StaffManagementRequiredMixin, CreateView):
    model = Institution
    form_class = InstitutionForm
    template_name = 'organization/institution/institution_form.html'
    success_url = reverse_lazy('organization:institution_list')

    def form_valid(self, form):
        messages.success(self.request, 'Institution created successfully!')
        return super().form_valid(form)


class InstitutionDetailView( StaffManagementRequiredMixin, DetailView):
    model = Institution
    template_name = 'organization/institution/institution_detail.html'
    context_object_name = 'institution'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = self.get_object()
        
        # Get related data
        context['departments'] = institution.departments.filter(is_active=True)
        context['branches'] = institution.branches.filter(is_active=True)
        context['affiliations'] = institution.affiliations.filter(is_active=True)
        context['accreditations'] = institution.accreditations.filter(is_active=True)
        context['partnerships'] = institution.partnerships.filter(is_active=True)
        
        return context


class InstitutionUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = Institution
    form_class = InstitutionForm
    template_name = 'organization/institution/institution_form.html'
    
    def get_success_url(self):
        return reverse('organization:institution_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Institution updated successfully!')
        return super().form_valid(form)


class InstitutionDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = Institution
    template_name = 'organization/institution/institution_confirm_delete.html'
    success_url = reverse_lazy('organization:institution_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Institution deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Department CRUD Views
class DepartmentCreateView( StaffManagementRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'organization/department/department_form.html'
    success_url = reverse_lazy('organization:department_list')

    def get_form_kwargs(self):
        """Pass the request to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        """Add context to template"""
        context = super().get_context_data(**kwargs)
        
        # Check if user can create departments
        user_has_institution = hasattr(self.request.user, 'institution') and self.request.user.institution
        context['can_create_department'] = user_has_institution or self.request.user.is_superuser
        context['user_institution'] = getattr(self.request.user, 'institution', None)
        
        return context

    def form_valid(self, form):
        """Handle valid form submission"""
        try:
            # Double-check institution assignment
            if not form.instance.institution:
                if hasattr(self.request.user, 'institution') and self.request.user.institution:
                    form.instance.institution = self.request.user.institution
                elif self.request.user.is_superuser and form.cleaned_data.get('institution'):
                    form.instance.institution = form.cleaned_data['institution']
                else:
                    form.add_error(None, "Unable to determine institution. Please select an institution.")
                    return self.form_invalid(form)
            
            # Save the department
            response = super().form_valid(form)
            messages.success(self.request, f'Department "{form.instance.name}" created successfully!')
            return response
            
        except Exception as e:
            messages.error(self.request, f'Error creating department: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        """Handle invalid form submission"""
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class DepartmentListView( ListView):
    model = Department
    template_name = 'organization/department/department_list.html'
    context_object_name = 'departments'
    
    def get_queryset(self):
        """Filter departments by user's institution or all for superusers"""
        queryset = super().get_queryset()
        
        if self.request.user.is_superuser:
            return queryset  # Superusers see all departments
        elif hasattr(self.request.user, 'institution') and self.request.user.institution:
            return queryset.filter(institution=self.request.user.institution)
        else:
            return Department.objects.none()  # Users without institution see nothing

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_has_institution'] = hasattr(self.request.user, 'institution') and self.request.user.institution
        return context

class DepartmentUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'organization/department/department_form.html'
    success_url = reverse_lazy('organization:department_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Department updated successfully!')
        return response

class DepartmentDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = Department
    template_name = 'organization/department/department_confirm_delete.html'
    success_url = reverse_lazy('organization:department_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Department deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Branch CRUD Views (similar pattern as Department)
class BranchListView( StaffManagementRequiredMixin, ListView):
    model = Branch
    template_name = 'organization/branch/branch_list.html'
    context_object_name = 'branches'
    paginate_by = 20

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Branch.objects.filter(institution=institution).order_by('name')


class BranchCreateView( StaffManagementRequiredMixin, CreateView):
    model = Branch
    form_class = BranchForm
    template_name = 'organization/branch/branch_form.html'
    success_url = reverse_lazy('organization:branch_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Branch created successfully!')
        return super().form_valid(form)


# Export Views
class InstitutionExportView( StaffManagementRequiredMixin, ListView):
    model = Institution
    context_object_name = 'institutions'

    def get_queryset(self):
        return Institution.objects.all()

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv')
        institutions = self.get_queryset()

        if format_type == 'csv':
            return self.export_csv(institutions)
        elif format_type == 'excel':
            return self.export_excel(institutions)
        elif format_type == 'pdf':
            return self.export_pdf(institutions)
        else:
            return redirect('organization:institution_list')

    def export_csv(self, institutions):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="institutions_{}.csv"'.format(
            datetime.now().strftime('%Y%m%d_%H%M%S')
        )

        writer = csv.writer(response)
        writer.writerow([
            'Name', 'Short Name', 'Code', 'Type', 'City', 'State', 'Country',
            'Contact Email', 'Contact Phone', 'Website', 'Status', 'Established Date'
        ])

        for institution in institutions:
            writer.writerow([
                institution.name,
                institution.short_name or '',
                institution.code,
                institution.get_type_display(),
                institution.city or '',
                institution.state or '',
                institution.country,
                institution.contact_email,
                institution.contact_phone,
                institution.website or '',
                'Active' if institution.is_active else 'Inactive',
                institution.established_date.strftime('%Y-%m-%d') if institution.established_date else ''
            ])

        return response

    def export_excel(self, institutions):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Institutions')

        # Add headers
        headers = [
            'Name', 'Short Name', 'Code', 'Type', 'City', 'State', 'Country',
            'Contact Email', 'Contact Phone', 'Website', 'Status', 'Established Date'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # Add data
        for row, institution in enumerate(institutions, start=1):
            worksheet.write(row, 0, institution.name)
            worksheet.write(row, 1, institution.short_name or '')
            worksheet.write(row, 2, institution.code)
            worksheet.write(row, 3, institution.get_type_display())
            worksheet.write(row, 4, institution.city or '')
            worksheet.write(row, 5, institution.state or '')
            worksheet.write(row, 6, institution.country)
            worksheet.write(row, 7, institution.contact_email)
            worksheet.write(row, 8, institution.contact_phone)
            worksheet.write(row, 9, institution.website or '')
            worksheet.write(row, 10, 'Active' if institution.is_active else 'Inactive')
            worksheet.write(row, 11, institution.established_date.strftime('%Y-%m-%d') if institution.established_date else '')

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="institutions_{}.xlsx"'.format(
            datetime.now().strftime('%Y%m%d_%H%M%S')
        )
        return response

    def export_pdf(self, institutions):
        # You'll need to implement PDF generation based on your PDF utility
        # This is a placeholder implementation
        return HttpResponse("PDF export not implemented yet")