import csv
from io import StringIO, BytesIO
from datetime import datetime, timedelta
import xlsxwriter
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.views.decorators.http import require_GET, require_POST
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import  PermissionRequiredMixin
from apps.core.mixins import LibraryManagerRequiredMixin
from apps.core.utils import get_user_institution
from .models import Reservation, Book
from .forms import ReservationForm, ReservationFilterForm
from django.utils.timezone import localtime
# Reservation List View
class ReservationListView(LibraryManagerRequiredMixin, ListView):
    model = Reservation
    template_name = 'library/reservations/reservation_list.html'
    context_object_name = 'reservations'
    paginate_by = 20
    permission_required = 'library.view_reservation'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = Reservation.objects.filter(institution=institution).select_related('book', 'user', 'institution')

        # Apply filters
        form = ReservationFilterForm(self.request.GET, institution=institution)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            status = form.cleaned_data.get('status')
            date_from = form.cleaned_data.get('date_from')
            date_to = form.cleaned_data.get('date_to')

            if search:
                queryset = queryset.filter(
                    Q(book__title__icontains=search) | 
                    Q(user__username__icontains=search) |
                    Q(user__first_name__icontains=search) |
                    Q(user__last_name__icontains=search) |
                    Q(notes__icontains=search)
                )
            if status:
                queryset = queryset.filter(status=status)
            if date_from:
                queryset = queryset.filter(reservation_date__date__gte=date_from)
            if date_to:
                queryset = queryset.filter(reservation_date__date__lte=date_to)

        return queryset.order_by('-reservation_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Statistics
        stats = Reservation.objects.filter(institution=institution).aggregate(
            total_reservations=Count('id'),
            pending_reservations=Count('id', filter=Q(status='pending')),
            fulfilled_reservations=Count('id', filter=Q(status='fulfilled')),
            cancelled_reservations=Count('id', filter=Q(status='cancelled')),
            expired_reservations=Count('id', filter=Q(status='expired'))
        )
        
        # Expiring reservations (within 2 days)
        expiring_reservations = Reservation.objects.filter(
            institution=institution,
            status='pending',
            expiry_date__lte=timezone.now() + timedelta(days=2),
            expiry_date__gte=timezone.now()
        ).count()
        
        context['filter_form'] = ReservationFilterForm(self.request.GET, institution=institution)
        context.update(stats)
        context['expiring_reservations'] = expiring_reservations
        return context

# Reservation Create View
class ReservationCreateView( LibraryManagerRequiredMixin,PermissionRequiredMixin, CreateView):
    model = Reservation
    form_class = ReservationForm
    template_name = 'library/reservations/reservation_form.html'
    permission_required = 'library.add_reservation'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, "Reservation created successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create New Reservation"
        return context

    def get_success_url(self):
        return reverse('library:reservation_detail', kwargs={'pk': self.object.pk})

# Reservation Update View
class ReservationUpdateView(LibraryManagerRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Reservation
    form_class = ReservationForm
    template_name = 'library/reservations/reservation_form.html'
    permission_required = 'library.change_reservation'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Reservation.objects.filter(institution=institution)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Reservation updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('library:reservation_detail', kwargs={'pk': self.object.pk})

# Reservation Detail View
class ReservationDetailView(LibraryManagerRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Reservation
    template_name = 'library/reservations/reservation_detail.html'
    context_object_name = 'reservation'
    permission_required = 'library.view_reservation'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Reservation.objects.filter(institution=institution)

# Reservation Delete View
class ReservationDeleteView( LibraryManagerRequiredMixin,PermissionRequiredMixin, DeleteView):
    model = Reservation
    template_name = 'library/reservations/reservation_confirm_delete.html'
    context_object_name = 'reservation'
    success_url = reverse_lazy('library:reservation_list')
    permission_required = 'library.delete_reservation'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Reservation.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        book_title = self.object.book.title
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Reservation for "{book_title}" has been deleted successfully.')
        return response

# Special Action Views
class ReservationFulfillView( LibraryManagerRequiredMixin,PermissionRequiredMixin, DetailView):
    model = Reservation
    permission_required = 'library.change_reservation'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Reservation.objects.filter(institution=institution)

    def get(self, request, *args, **kwargs):
        reservation = self.get_object()
        if reservation.status == 'pending':
            reservation.status = 'fulfilled'
            reservation.save()
            messages.success(request, f'Reservation for "{reservation.book.title}" has been marked as fulfilled.')
        else:
            messages.warning(request, 'Only pending reservations can be fulfilled.')
        
        return redirect('library:reservation_detail', pk=reservation.pk)

class ReservationCancelView(LibraryManagerRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Reservation
    permission_required = 'library.change_reservation'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Reservation.objects.filter(institution=institution)

    def get(self, request, *args, **kwargs):
        reservation = self.get_object()
        if reservation.status == 'pending':
            reservation.status = 'cancelled'
            reservation.save()
            messages.success(request, f'Reservation for "{reservation.book.title}" has been cancelled.')
        else:
            messages.warning(request, 'Only pending reservations can be cancelled.')
        
        return redirect('library:reservation_detail', pk=reservation.pk)

# Export Views
class ReservationExportView(LibraryManagerRequiredMixin, PermissionRequiredMixin, ListView):
    model = Reservation
    context_object_name = "reservations"
    permission_required = 'library.view_reservation'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = Reservation.objects.select_related('book', 'user', 'institution').filter(institution=institution)
        
        # Apply filters from request
        form = ReservationFilterForm(self.request.GET, institution=institution)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            status = form.cleaned_data.get('status')
            date_from = form.cleaned_data.get('date_from')
            date_to = form.cleaned_data.get('date_to')
            
            if search:
                queryset = queryset.filter(
                    Q(book__title__icontains=search) | 
                    Q(user__username__icontains=search) |
                    Q(user__first_name__icontains=search) |
                    Q(user__last_name__icontains=search) |
                    Q(notes__icontains=search)
                )
            if status:
                queryset = queryset.filter(status=status)
            if date_from:
                queryset = queryset.filter(reservation_date__date__gte=date_from)
            if date_to:
                queryset = queryset.filter(reservation_date__date__lte=date_to)
        
        return queryset.order_by('-reservation_date')

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "csv").lower()
        queryset = self.get_queryset()

        filename = f"reservations_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        organization = get_user_institution(request.user)

        if format_type == "csv":
            return self.export_csv(queryset, filename, organization)
        elif format_type == "excel":
            return self.export_excel(queryset, filename, organization)
        elif format_type == "pdf":
            return self.export_pdf(queryset, filename, organization)
        return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, queryset, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        # Write headers
        writer.writerow([
            'Reservation ID', 'Book Title', 'Author', 'ISBN', 'User Name', 
            'User Email', 'Reservation Date', 'Expiry Date', 'Status', 
            'Days Remaining', 'Notes', 'Institution'
        ])

        # Write data
        for reservation in queryset:
            days_remaining = max(0, (reservation.expiry_date - timezone.now()).days) if reservation.status == 'pending' else 0
            
            writer.writerow([
                str(reservation.id),
                reservation.book.title,
                reservation.book.author.name if reservation.book.author else '',
                reservation.book.isbn or '',
                f"{reservation.user.get_full_name() or reservation.user.username}",
                reservation.user.email or '',
                reservation.reservation_date.strftime('%Y-%m-%d %H:%M'),
                reservation.expiry_date.strftime('%Y-%m-%d %H:%M'),
                reservation.get_status_display(),
                days_remaining if reservation.status == 'pending' else 'N/A',
                reservation.notes or '',
                organization.name
            ])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, queryset, filename, organization):
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Reservations")

            # Define formats
            header_format = workbook.add_format({
                "bold": True, 
                "bg_color": "#2c3e50", 
                "font_color": "white",
                "border": 1, 
                "align": "center", 
                "valign": "vcenter"
            })
            
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})
            center_format = workbook.add_format({'align': 'center'})

            # Write headers
            headers = [
                'Reservation ID', 'Book Title', 'Author', 'ISBN', 'User Name', 
                'User Email', 'Reservation Date', 'Expiry Date', 'Status', 
                'Days Remaining', 'Notes'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            # Write data
            for row_idx, reservation in enumerate(queryset, start=1):
                days_remaining = max(0, (reservation.expiry_date - timezone.now()).days) if reservation.status == 'pending' else 0
                
                worksheet.write(row_idx, 0, str(reservation.id))
                worksheet.write(row_idx, 1, reservation.book.title)
                worksheet.write(row_idx, 2, reservation.book.author.name if reservation.book.author else '')
                worksheet.write(row_idx, 3, reservation.book.isbn or '')
                worksheet.write(row_idx, 4, f"{reservation.user.get_full_name() or ''}")
                worksheet.write(row_idx, 5, reservation.user.email or '')
              
                
                worksheet.write(row_idx, 6, reservation.get_status_display())
                worksheet.write(row_idx, 7, days_remaining if reservation.status == 'pending' else 'N/A', center_format)
                worksheet.write(row_idx, 8, reservation.notes or '')

            # Set column widths
            worksheet.set_column('A:A', 36)  # Reservation ID
            worksheet.set_column('B:B', 30)  # Book Title
            worksheet.set_column('C:C', 25)  # Author
            worksheet.set_column('D:D', 15)  # ISBN
            worksheet.set_column('E:E', 25)  # User Name
            worksheet.set_column('F:F', 25)  # User Email
            worksheet.set_column('G:H', 18)  # Dates
            worksheet.set_column('I:I', 15)  # Status
            worksheet.set_column('J:J', 12)  # Days Remaining
            worksheet.set_column('K:K', 40)  # Notes

            # Add summary statistics
            stats_row = len(queryset) + 2
            worksheet.write(stats_row, 0, "Export Summary", header_format)
            worksheet.write(stats_row + 1, 0, "Total Reservations:")
            worksheet.write(stats_row + 1, 1, len(queryset))
            worksheet.write(stats_row + 2, 0, "Pending:")
            worksheet.write(stats_row + 2, 1, queryset.filter(status='pending').count())
            worksheet.write(stats_row + 3, 0, "Fulfilled:")
            worksheet.write(stats_row + 3, 1, queryset.filter(status='fulfilled').count())
            worksheet.write(stats_row + 4, 0, "Cancelled:")
            worksheet.write(stats_row + 4, 1, queryset.filter(status='cancelled').count())
            worksheet.write(stats_row + 5, 0, "Expired:")
            worksheet.write(stats_row + 5, 1, queryset.filter(status='expired').count())

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, queryset, filename, organization):
        from utils.utils import render_to_pdf, export_pdf_response
        
        context = {
            "reservations": queryset,
            "total_count": queryset.count(),
            "pending_count": queryset.filter(status='pending').count(),
            "fulfilled_count": queryset.filter(status='fulfilled').count(),
            "cancelled_count": queryset.filter(status='cancelled').count(),
            "expired_count": queryset.filter(status='expired').count(),
            "export_date": timezone.now(),
            "organization": organization,
            "filters": self.request.GET.dict(),
            "logo": getattr(organization, 'logo', None) and organization.logo.url if organization and hasattr(organization, 'logo') else None,
            "stamp": getattr(organization, 'stamp', None) and organization.stamp.url if organization and hasattr(organization, 'stamp') else None,
            "title": "Reservations Export Report",
        }
        
        pdf_bytes = render_to_pdf("library/export/reservations_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)


# Individual Reservation Export
class ReservationDetailExportView( LibraryManagerRequiredMixin,PermissionRequiredMixin, DetailView):
    model = Reservation
    permission_required = 'library.view_reservation'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Reservation.objects.filter(institution=institution)

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "pdf").lower()
        reservation = self.get_object()
        organization = get_user_institution(request.user)

        filename = f"reservation_{reservation.id}_{timezone.now().strftime('%Y%m%d')}"

        if format_type == "pdf":
            return self.export_pdf(reservation, filename, organization)
        elif format_type == "receipt":
            return self.export_receipt(reservation, filename, organization)
        elif format_type == "csv":
            return self.export_csv(reservation, filename)
        elif format_type == "excel":
            return self.export_excel(reservation, filename)
        return HttpResponse("Invalid format specified", status=400)

    def export_pdf(self, reservation, filename, organization):
        from utils.utils import render_to_pdf, export_pdf_response
        
        context = {
            "reservation": reservation,
            "organization": organization,
            "export_date": timezone.now(),
            "logo": getattr(organization, 'logo', None) and organization.logo.url if organization and hasattr(organization, 'logo') else None,
            "is_expired": reservation.expiry_date < timezone.now() and reservation.status == 'pending',
            "days_remaining": max(0, (reservation.expiry_date - timezone.now()).days) if reservation.status == 'pending' else 0,
        }
        
        pdf_bytes = render_to_pdf("library/export/reservation_detail_pdf.html", context)
        if pdf_bytes:
            from utils.utils import export_pdf_response
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

    def export_receipt(self, reservation, filename, organization):
        from apps.core.utils import render_to_pdf, export_pdf_response
        
        context = {
            "reservation": reservation,
            "organization": organization,
            "export_date": timezone.now(),
            "logo": getattr(organization, 'logo', None) and organization.logo.url if organization and hasattr(organization, 'logo') else None,
        }
        
        pdf_bytes = render_to_pdf("library/reservations/export/reservation_receipt_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}_receipt.pdf")
        return HttpResponse("Error generating PDF", status=500)

    def export_csv(self, reservation, filename):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

        writer = csv.writer(response)
        # Header
        writer.writerow(['Reservation ID', 'Book', 'User', 'Reservation Date', 'Expiry Date', 'Status', 'Notes'])
        # Data
        writer.writerow([
            reservation.id,
            reservation.book.title,
            reservation.user.username,
            reservation.reservation_date.strftime('%Y-%m-%d %H:%M'),
            reservation.expiry_date.strftime('%Y-%m-%d %H:%M'),
            reservation.status,
            reservation.notes or ''
        ])
        return response

    def export_excel(self, reservation, filename):
  
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Reservation")

            # Define formats
            header_format = workbook.add_format({
                "bold": True, 
                "bg_color": "#2c3e50", 
                "font_color": "white",
                "border": 1, 
                "align": "center", 
                "valign": "vcenter"
            })
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm', 'align': 'center'})
            center_format = workbook.add_format({'align': 'center'})

            # Write headers
            headers = [
                'Reservation ID', 'Book Title', 'Author', 'ISBN', 'User Name', 
                'User Email', 'Reservation Date', 'Expiry Date', 'Status', 'Days Remaining', 'Notes'
            ]
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            # Calculate days remaining
            days_remaining = max(0, (reservation.expiry_date - timezone.now()).days) if reservation.status == 'pending' else 0

            # Write reservation data
            worksheet.write(1, 0, str(reservation.id))
            worksheet.write(1, 1, reservation.book.title)
            worksheet.write(1, 2, reservation.book.author.name if reservation.book.author else '')
            worksheet.write(1, 3, reservation.book.isbn or '')
            worksheet.write(1, 4, reservation.user.get_full_name() or '')
            worksheet.write(1, 5, reservation.user.email or '')
            worksheet.write_datetime(1, 6, reservation.reservation_date.replace(tzinfo=None), date_format)
            worksheet.write_datetime(1, 7, reservation.expiry_date.replace(tzinfo=None), date_format)
            worksheet.write(1, 8, reservation.get_status_display(), center_format)
            worksheet.write(1, 9, days_remaining if reservation.status == 'pending' else 'N/A', center_format)
            worksheet.write(1, 10, reservation.notes or '')

            # Set column widths
            worksheet.set_column('A:A', 36)
            worksheet.set_column('B:B', 30)
            worksheet.set_column('C:C', 25)
            worksheet.set_column('D:D', 15)
            worksheet.set_column('E:E', 25)
            worksheet.set_column('F:F', 25)
            worksheet.set_column('G:H', 18)
            worksheet.set_column('I:I', 15)
            worksheet.set_column('J:J', 12)
            worksheet.set_column('K:K', 40)

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response


# API Views
@require_GET
def get_reservation_details(request, pk):
    """API endpoint to get reservation details"""
    institution = get_user_institution(request.user)
    reservation = get_object_or_404(Reservation, pk=pk, institution=institution)
    
    return JsonResponse({
        'book_title': reservation.book.title,
        'user_name': f"{reservation.user.get_full_name() or reservation.user.username}",
        'reservation_date': reservation.reservation_date.strftime('%Y-%m-%d %H:%M'),
        'expiry_date': reservation.expiry_date.strftime('%Y-%m-%d %H:%M'),
        'status': reservation.get_status_display(),
        'notes': reservation.notes or '',
        'is_expired': reservation.expiry_date < timezone.now() and reservation.status == 'pending'
    })