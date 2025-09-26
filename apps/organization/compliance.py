from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from apps.core.mixins import StaffManagementRequiredMixin
from .models import InstitutionCompliance
from .forms import InstitutionComplianceForm
import csv
from io import BytesIO
import xlsxwriter
from datetime import datetime
from apps.core.utils import get_user_institution

# ------------------ Compliance CRUD ------------------ #

class InstitutionComplianceListView( StaffManagementRequiredMixin, ListView):
    model = InstitutionCompliance
    template_name = 'organization/compliance/compliance_list.html'
    context_object_name = 'compliances'
    paginate_by = 20

    def get_queryset(self):
        """Filter compliances by user's institution"""
        queryset = super().get_queryset().select_related('institution')
        
        # Superusers can see all, regular users see only their institution's compliances
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                # Users without institution see nothing
                queryset = InstitutionCompliance.objects.none()
                
        return queryset

class InstitutionComplianceCreateView( StaffManagementRequiredMixin, CreateView):
    model = InstitutionCompliance
    form_class = InstitutionComplianceForm
    template_name = 'organization/compliance/compliance_form.html'
    success_url = reverse_lazy('organization:compliance_list')

    def get_form_kwargs(self):
        """Pass the request to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """Handle valid form submission with institution assignment"""
        try:
            # Ensure institution is set
            if not form.instance.institution:
                user_institution = get_user_institution(self.request.user)
                if user_institution:
                    form.instance.institution = user_institution
                else:
                    form.add_error(None, "You need to be associated with an institution to create compliance records.")
                    return self.form_invalid(form)
            
            messages.success(self.request, "Compliance record created successfully!")
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f"Error creating compliance record: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

class InstitutionComplianceUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = InstitutionCompliance
    form_class = InstitutionComplianceForm
    template_name = 'organization/compliance/compliance_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_queryset(self):
        """Filter to only allow editing own institution's compliances (unless superuser)"""
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = InstitutionCompliance.objects.none()
        return queryset

    def get_success_url(self):
        return reverse('organization:compliance_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Compliance record updated successfully!")
        return super().form_valid(form)

class InstitutionComplianceDetailView( StaffManagementRequiredMixin, DetailView):
    model = InstitutionCompliance
    template_name = 'organization/compliance/compliance_detail.html'
    context_object_name = 'compliance'

    def get_queryset(self):
        """Filter to only allow viewing own institution's compliances (unless superuser)"""
        queryset = super().get_queryset().select_related('institution')
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = InstitutionCompliance.objects.none()
        return queryset

class InstitutionComplianceDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = InstitutionCompliance
    template_name = 'organization/compliance/compliance_confirm_delete.html'
    success_url = reverse_lazy('organization:compliance_list')

    def get_queryset(self):
        """Filter to only allow deleting own institution's compliances (unless superuser)"""
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = InstitutionCompliance.objects.none()
        return queryset

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Compliance record deleted successfully!")
        return super().delete(request, *args, **kwargs)

# ------------------ Export Views ------------------ #

class InstitutionComplianceExportView( StaffManagementRequiredMixin, ListView):
    model = InstitutionCompliance

    def get_queryset(self):
        """Filter exports by user's institution"""
        queryset = InstitutionCompliance.objects.select_related('institution').all()
        
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = InstitutionCompliance.objects.none()
                
        return queryset

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv')
        compliances = self.get_queryset()
        
        if format_type == 'csv':
            return self.export_csv(compliances)
        elif format_type == 'excel':
            return self.export_excel(compliances)
        else:
            return HttpResponse("Invalid format", status=400)

    def export_csv(self, compliances):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="compliances_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Institution', 'GST Number', 'PAN Number', 'TAN Number',
            'Registration No', 'Registration Authority', 'Registration Date',
            'PF No', 'ESI No', 'UDISE', 'AICTE', 'UGC', 'Status'
        ])
        
        for compliance in compliances:
            writer.writerow([
                compliance.institution.name,
                compliance.gst_number or '',
                compliance.pan_number or '',
                compliance.tan_number or '',
                compliance.registration_no or '',
                compliance.registration_authority or '',
                compliance.registration_date.strftime('%Y-%m-%d') if compliance.registration_date else '',
                compliance.pf_registration_no or '',
                compliance.esi_registration_no or '',
                compliance.udise_code or '',
                compliance.aicte_code or '',
                compliance.ugc_code or '',
                'Active' if compliance.is_active else 'Inactive'
            ])
        return response

    def export_excel(self, compliances):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Compliances')
        
        # Add headers
        headers = [
            'Institution', 'GST Number', 'PAN Number', 'TAN Number',
            'Registration No', 'Registration Authority', 'Registration Date',
            'PF No', 'ESI No', 'UDISE', 'AICTE', 'UGC', 'Status'
        ]
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)
        
        # Write data
        for row, compliance in enumerate(compliances, start=1):
            worksheet.write(row, 0, compliance.institution.name)
            worksheet.write(row, 1, compliance.gst_number or '')
            worksheet.write(row, 2, compliance.pan_number or '')
            worksheet.write(row, 3, compliance.tan_number or '')
            worksheet.write(row, 4, compliance.registration_no or '')
            worksheet.write(row, 5, compliance.registration_authority or '')
            worksheet.write(row, 6, compliance.registration_date.strftime('%Y-%m-%d') if compliance.registration_date else '')
            worksheet.write(row, 7, compliance.pf_registration_no or '')
            worksheet.write(row, 8, compliance.esi_registration_no or '')
            worksheet.write(row, 9, compliance.udise_code or '')
            worksheet.write(row, 10, compliance.aicte_code or '')
            worksheet.write(row, 11, compliance.ugc_code or '')
            worksheet.write(row, 12, 'Active' if compliance.is_active else 'Inactive')
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="compliances_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        return response