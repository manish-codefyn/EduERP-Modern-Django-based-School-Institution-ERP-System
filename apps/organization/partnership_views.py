from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from apps.core.mixins import StaffManagementRequiredMixin
from .models import Partnership
from .forms import PartnershipForm
import csv
from io import BytesIO
import xlsxwriter
from datetime import datetime, timedelta
from apps.core.utils import get_user_institution

# ------------------ Partnership CRUD ------------------ #

class PartnershipListView( StaffManagementRequiredMixin, ListView):
    model = Partnership
    template_name = 'organization/partnership/partnership_list.html'
    context_object_name = 'partnerships'
    paginate_by = 20

    def get_queryset(self):
        """Filter partnerships by user's institution"""
        queryset = super().get_queryset().select_related('institution')
        
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Partnership.objects.none()
                
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add statistics for the template
        queryset = self.get_queryset()
        context['total_partnerships'] = queryset.count()
        context['active_partnerships'] = queryset.filter(is_active=True).count()
        context['expiring_soon'] = queryset.filter(
            is_active=True,
            end_date__lte=datetime.now().date() + timedelta(days=90),
            end_date__gte=datetime.now().date()
        ).count()
        
        # Partner type statistics
        context['industry_count'] = queryset.filter(partner_type='industry').count()
        context['university_count'] = queryset.filter(partner_type='foreign_university').count()
        
        return context

class PartnershipCreateView( StaffManagementRequiredMixin, CreateView):
    model = Partnership
    form_class = PartnershipForm
    template_name = 'organization/partnership/partnership_form.html'
    success_url = reverse_lazy('organization:partnership_list')

    def get_form_kwargs(self):
        """Pass the request to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """Handle valid form submission with institution assignment"""
        try:
            # Ensure institution is set
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                form.instance.institution = user_institution
            else:
                form.add_error(None, "You need to be associated with an institution to create partnership records.")
                return self.form_invalid(form)
            
            messages.success(self.request, "Partnership record created successfully!")
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f"Error creating partnership record: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

class PartnershipUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = Partnership
    form_class = PartnershipForm
    template_name = 'organization/partnership/partnership_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_queryset(self):
        """Filter to only allow editing own institution's partnerships"""
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Partnership.objects.none()
        return queryset

    def get_success_url(self):
        return reverse('organization:partnership_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Partnership record updated successfully!")
        return super().form_valid(form)

class PartnershipDetailView( StaffManagementRequiredMixin, DetailView):
    model = Partnership
    template_name = 'organization/partnership/partnership_detail.html'
    context_object_name = 'partnership'

    def get_queryset(self):
        """Filter to only allow viewing own institution's partnerships"""
        queryset = super().get_queryset().select_related('institution')
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Partnership.objects.none()
        return queryset

class PartnershipDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = Partnership
    template_name = 'organization/partnership/partnership_confirm_delete.html'
    success_url = reverse_lazy('organization:partnership_list')

    def get_queryset(self):
        """Filter to only allow deleting own institution's partnerships"""
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Partnership.objects.none()
        return queryset

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Partnership record deleted successfully!")
        return super().delete(request, *args, **kwargs)

# ------------------ Export Views ------------------ #

class PartnershipExportView( StaffManagementRequiredMixin, ListView):
    model = Partnership

    def get_queryset(self):
        """Filter exports by user's institution"""
        queryset = Partnership.objects.select_related('institution').all()
        
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Partnership.objects.none()
                
        return queryset

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv')
        partnerships = self.get_queryset()
        
        if format_type == 'csv':
            return self.export_csv(partnerships)
        elif format_type == 'excel':
            return self.export_excel(partnerships)
        else:
            return HttpResponse("Invalid format", status=400)

    def export_csv(self, partnerships):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="partnerships_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Institution', 'Partner Name', 'Partner Type', 'Description',
            'Start Date', 'End Date', 'Contact Person', 'Contact Email',
            'Contact Phone', 'Renewal Required', 'Status'
        ])
        
        for partnership in partnerships:
            writer.writerow([
                partnership.institution.name,
                partnership.partner_name,
                partnership.get_partner_type_display(),
                partnership.description or '',
                partnership.start_date.strftime('%Y-%m-%d') if partnership.start_date else '',
                partnership.end_date.strftime('%Y-%m-%d') if partnership.end_date else '',
                partnership.contact_person or '',
                partnership.contact_email or '',
                partnership.contact_phone or '',
                'Yes' if partnership.renewal_required else 'No',
                'Active' if partnership.is_active else 'Inactive'
            ])
        return response

    def export_excel(self, partnerships):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Partnerships')
        
        # Add headers
        headers = [
            'Institution', 'Partner Name', 'Partner Type', 'Description',
            'Start Date', 'End Date', 'Contact Person', 'Contact Email',
            'Contact Phone', 'Renewal Required', 'Status'
        ]
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)
        
        # Write data
        for row, partnership in enumerate(partnerships, start=1):
            worksheet.write(row, 0, partnership.institution.name)
            worksheet.write(row, 1, partnership.partner_name)
            worksheet.write(row, 2, partnership.get_partner_type_display())
            worksheet.write(row, 3, partnership.description or '')
            worksheet.write(row, 4, partnership.start_date.strftime('%Y-%m-%d') if partnership.start_date else '')
            worksheet.write(row, 5, partnership.end_date.strftime('%Y-%m-%d') if partnership.end_date else '')
            worksheet.write(row, 6, partnership.contact_person or '')
            worksheet.write(row, 7, partnership.contact_email or '')
            worksheet.write(row, 8, partnership.contact_phone or '')
            worksheet.write(row, 9, 'Yes' if partnership.renewal_required else 'No')
            worksheet.write(row, 10, 'Active' if partnership.is_active else 'Inactive')
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="partnerships_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        return response