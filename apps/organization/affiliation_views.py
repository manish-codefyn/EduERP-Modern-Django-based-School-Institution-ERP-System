from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from datetime import timedelta, datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from apps.core.mixins import StaffManagementRequiredMixin
from .models import Affiliation
from .forms import AffiliationForm
import csv
from io import BytesIO
import xlsxwriter
from apps.core.utils import get_user_institution


# ------------------ Affiliation CRUD ------------------ #

class AffiliationListView( StaffManagementRequiredMixin, ListView):
    model = Affiliation
    template_name = 'organization/affiliation/affiliation_list.html'
    context_object_name = 'affiliations'
    paginate_by = 20

    def get_queryset(self):
        """Filter affiliations by user's institution"""
        queryset = super().get_queryset().select_related('institution')
        
        # Superusers can see all, regular users see only their institution's affiliations
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                # Users without institution see nothing
                queryset = Affiliation.objects.none()
                
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add statistics for the template
        queryset = self.get_queryset()
        context['total_affiliations'] = queryset.count()
        context['active_affiliations'] = queryset.filter(is_active=True).count()
        context['expiring_soon'] = queryset.filter(
            is_active=True,
            valid_to__lte=datetime.now().date() + timedelta(days=90),
            valid_to__gte=datetime.now().date()
        ).count()
        
        return context


class AffiliationCreateView( StaffManagementRequiredMixin, CreateView):
    model = Affiliation
    form_class = AffiliationForm
    template_name = 'organization/affiliation/affiliation_form.html'
    success_url = reverse_lazy('organization:affiliation_list')

    def get_form_kwargs(self):
        """Pass the request to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """Handle valid form submission with institution assignment"""
        try:
            # Ensure institution is set (only in the view, not in the form)
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                form.instance.institution = user_institution
            else:
                form.add_error(None, "You need to be associated with an institution to create affiliation records.")
                return self.form_invalid(form)
            
            messages.success(self.request, "Affiliation record created successfully!")
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f"Error creating affiliation record: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class AffiliationUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = Affiliation
    form_class = AffiliationForm
    template_name = 'organization/affiliation/affiliation_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_queryset(self):
        """Filter to only allow editing own institution's affiliations (unless superuser)"""
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Affiliation.objects.none()
        return queryset

    def get_success_url(self):
        return reverse('organization:affiliation_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Affiliation record updated successfully!")
        return super().form_valid(form)


class AffiliationDetailView( StaffManagementRequiredMixin, DetailView):
    model = Affiliation
    template_name = 'organization/affiliation/affiliation_detail.html'
    context_object_name = 'affiliation'

    def get_queryset(self):
        """Filter to only allow viewing own institution's affiliations (unless superuser)"""
        queryset = super().get_queryset().select_related('institution')
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Affiliation.objects.none()
        return queryset


class AffiliationDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = Affiliation
    template_name = 'organization/affiliation/affiliation_confirm_delete.html'
    success_url = reverse_lazy('organization:affiliation_list')

    def get_queryset(self):
        """Filter to only allow deleting own institution's affiliations (unless superuser)"""
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Affiliation.objects.none()
        return queryset

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Affiliation record deleted successfully!")
        return super().delete(request, *args, **kwargs)


# ------------------ Export Views ------------------ #

class AffiliationExportView( StaffManagementRequiredMixin, ListView):
    model = Affiliation

    def get_queryset(self):
        """Filter exports by user's institution"""
        queryset = Affiliation.objects.select_related('institution').all()
        
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Affiliation.objects.none()
                
        return queryset

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv')
        affiliations = self.get_queryset()
        
        if format_type == 'csv':
            return self.export_csv(affiliations)
        elif format_type == 'excel':
            return self.export_excel(affiliations)
        else:
            return HttpResponse("Invalid format", status=400)

    def export_csv(self, affiliations):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="affiliations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Institution', 'Affiliation Name', 'Code', 'Valid From', 
            'Valid To', 'Renewal Required', 'Status', 'Days Until Expiry'
        ])
        
        for affiliation in affiliations:
            days_until_expiry = None
            if affiliation.valid_to:
                days_until_expiry = (affiliation.valid_to - datetime.now().date()).days
            
            writer.writerow([
                affiliation.institution.name,
                affiliation.name,
                affiliation.code or '',
                affiliation.valid_from.strftime('%Y-%m-%d') if affiliation.valid_from else '',
                affiliation.valid_to.strftime('%Y-%m-%d') if affiliation.valid_to else '',
                'Yes' if affiliation.renewal_required else 'No',
                'Active' if affiliation.is_active else 'Inactive',
                days_until_expiry if days_until_expiry is not None else 'N/A'
            ])
        return response

    def export_excel(self, affiliations):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Affiliations')
        
        # Add headers
        headers = [
            'Institution', 'Affiliation Name', 'Code', 'Valid From', 
            'Valid To', 'Renewal Required', 'Status', 'Days Until Expiry'
        ]
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)
        
        # Write data
        for row, affiliation in enumerate(affiliations, start=1):
            days_until_expiry = None
            if affiliation.valid_to:
                days_until_expiry = (affiliation.valid_to - datetime.now().date()).days
            
            worksheet.write(row, 0, affiliation.institution.name)
            worksheet.write(row, 1, affiliation.name)
            worksheet.write(row, 2, affiliation.code or '')
            worksheet.write(row, 3, affiliation.valid_from.strftime('%Y-%m-%d') if affiliation.valid_from else '')
            worksheet.write(row, 4, affiliation.valid_to.strftime('%Y-%m-%d') if affiliation.valid_to else '')
            worksheet.write(row, 5, 'Yes' if affiliation.renewal_required else 'No')
            worksheet.write(row, 6, 'Active' if affiliation.is_active else 'Inactive')
            worksheet.write(row, 7, days_until_expiry if days_until_expiry is not None else 'N/A')
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="affiliations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        return response