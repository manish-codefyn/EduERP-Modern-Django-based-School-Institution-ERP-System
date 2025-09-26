from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from datetime import datetime,timedelta
from apps.core.mixins import StaffManagementRequiredMixin
from .models import Accreditation
from .forms import AccreditationForm
import csv
from io import BytesIO
import xlsxwriter
from datetime import datetime
from apps.core.utils import get_user_institution

# ------------------ Accreditation CRUD ------------------ #
class AccreditationListView( StaffManagementRequiredMixin, ListView):
    model = Accreditation
    template_name = 'organization/accreditation/accreditation_list.html'
    context_object_name = 'accreditations'
    paginate_by = 20

    def get_queryset(self):
        """Filter accreditations by user's institution"""
        queryset = super().get_queryset().select_related('institution')
        
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Accreditation.objects.none()
                
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add statistics for the template
        queryset = self.get_queryset()
        context['total_accreditations'] = queryset.count()
        context['active_accreditations'] = queryset.filter(is_active=True).count()
        context['expiring_soon'] = queryset.filter(
            is_active=True,
            valid_to__lte=datetime.now().date() + timedelta(days=90),
            valid_to__gte=datetime.now().date()
        ).count()
        context['naac_count'] = queryset.filter(name__icontains='NAAC').count()
        
        return context

class AccreditationCreateView( StaffManagementRequiredMixin, CreateView):
    model = Accreditation
    form_class = AccreditationForm
    template_name = 'organization/accreditation/accreditation_form.html'
    success_url = reverse_lazy('organization:accreditation_list')

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
                form.add_error(None, "You need to be associated with an institution to create accreditation records.")
                return self.form_invalid(form)
            
            messages.success(self.request, "Accreditation record created successfully!")
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f"Error creating accreditation record: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

class AccreditationUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = Accreditation
    form_class = AccreditationForm
    template_name = 'organization/accreditation/accreditation_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_queryset(self):
        """Filter to only allow editing own institution's accreditations"""
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Accreditation.objects.none()
        return queryset

    def get_success_url(self):
        return reverse('organization:accreditation_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Accreditation record updated successfully!")
        return super().form_valid(form)

class AccreditationDetailView( StaffManagementRequiredMixin, DetailView):
    model = Accreditation
    template_name = 'organization/accreditation/accreditation_detail.html'
    context_object_name = 'accreditation'

    def get_queryset(self):
        """Filter to only allow viewing own institution's accreditations"""
        queryset = super().get_queryset().select_related('institution')
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Accreditation.objects.none()
        return queryset

class AccreditationDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = Accreditation
    template_name = 'organization/accreditation/accreditation_confirm_delete.html'
    success_url = reverse_lazy('organization:accreditation_list')

    def get_queryset(self):
        """Filter to only allow deleting own institution's accreditations"""
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Accreditation.objects.none()
        return queryset

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Accreditation record deleted successfully!")
        return super().delete(request, *args, **kwargs)

# ------------------ Export Views ------------------ #

class AccreditationExportView( StaffManagementRequiredMixin, ListView):
    model = Accreditation

    def get_queryset(self):
        """Filter exports by user's institution"""
        queryset = Accreditation.objects.select_related('institution').all()
        
        if not self.request.user.is_superuser:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                queryset = queryset.filter(institution=user_institution)
            else:
                queryset = Accreditation.objects.none()
                
        return queryset

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv')
        accreditations = self.get_queryset()
        
        if format_type == 'csv':
            return self.export_csv(accreditations)
        elif format_type == 'excel':
            return self.export_excel(accreditations)
        else:
            return HttpResponse("Invalid format", status=400)

    def export_csv(self, accreditations):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="accreditations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Institution', 'Accreditation Name', 'Grade/Level', 'Awarded By',
            'Valid From', 'Valid To', 'Renewal Required', 'Status'
        ])
        
        for accreditation in accreditations:
            writer.writerow([
                accreditation.institution.name,
                accreditation.name,
                accreditation.grade_or_level or '',
                accreditation.awarded_by or '',
                accreditation.valid_from.strftime('%Y-%m-%d') if accreditation.valid_from else '',
                accreditation.valid_to.strftime('%Y-%m-%d') if accreditation.valid_to else '',
                'Yes' if accreditation.renewal_required else 'No',
                'Active' if accreditation.is_active else 'Inactive'
            ])
        return response

    def export_excel(self, accreditations):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Accreditations')
        
        # Add headers
        headers = [
            'Institution', 'Accreditation Name', 'Grade/Level', 'Awarded By',
            'Valid From', 'Valid To', 'Renewal Required', 'Status'
        ]
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)
        
        # Write data
        for row, accreditation in enumerate(accreditations, start=1):
            worksheet.write(row, 0, accreditation.institution.name)
            worksheet.write(row, 1, accreditation.name)
            worksheet.write(row, 2, accreditation.grade_or_level or '')
            worksheet.write(row, 3, accreditation.awarded_by or '')
            worksheet.write(row, 4, accreditation.valid_from.strftime('%Y-%m-%d') if accreditation.valid_from else '')
            worksheet.write(row, 5, accreditation.valid_to.strftime('%Y-%m-%d') if accreditation.valid_to else '')
            worksheet.write(row, 6, 'Yes' if accreditation.renewal_required else 'No')
            worksheet.write(row, 7, 'Active' if accreditation.is_active else 'Inactive')
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="accreditations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        return response