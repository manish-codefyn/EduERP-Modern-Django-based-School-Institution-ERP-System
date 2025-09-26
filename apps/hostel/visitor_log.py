
from django.shortcuts import get_object_or_404,redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView,View
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count
from .models import HostelVisitorLog
from .forms import HostelVisitorLogForm
from apps.core.utils import get_user_institution
from apps.core.mixins import FinanceAccessRequiredMixin,DirectorRequiredMixin
from utils.utils import render_to_pdf, export_pdf_response
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import HttpResponse
from django.utils import timezone
from io import StringIO, BytesIO
import csv
import xlsxwriter



class HostelVisitorLogExportView(FinanceAccessRequiredMixin, View):
    """
    Export Hostel Visitor Log data in CSV, PDF, Excel formats
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        institution = get_user_institution(request.user)
        qs = HostelVisitorLog.objects.filter(institution=institution)

        if start_date:
            qs = qs.filter(entry_time__date__gte=start_date)
        if end_date:
            qs = qs.filter(entry_time__date__lte=end_date)

        qs = qs.order_by("-entry_time")

        filename_parts = ["visitor_logs"]
        if start_date:
            filename_parts.append(f"from_{start_date}")
        if end_date:
            filename_parts.append(f"to_{end_date}")
        filename = "_".join(filename_parts).lower()

        rows = []
        for log in qs:
            rows.append({
                "visitor_name": log.visitor_name,
                "student_visited": log.student_visited.user.get_full_name() if log.student_visited else "N/A",
                "purpose": log.purpose,
                "id_proof": log.get_id_proof_display() if log.id_proof else "-",
                "id_number": log.id_number or "-",
                "entry_time": log.entry_time.strftime("%Y-%m-%d %H:%M"),
                "exit_time": log.exit_time.strftime("%Y-%m-%d %H:%M") if log.exit_time else "-",
                "recorded_by": log.recorded_by.user.get_full_name() if log.recorded_by else "N/A",
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
            "Visitor Name", "Student Visited", "Purpose", "ID Proof", "ID Number",
            "Entry Time", "Exit Time", "Recorded By"
        ])

        for row in rows:
            writer.writerow([
                row["visitor_name"], row["student_visited"], row["purpose"],
                row["id_proof"], row["id_number"], row["entry_time"],
                row["exit_time"], row["recorded_by"]
            ])

        writer.writerow([])
        writer.writerow(["Total Visitors:", len(rows)])
        writer.writerow(["Organization:", organization.name if organization else "N/A"])
        writer.writerow(["Export Date:", timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_pdf(self, rows, filename, organization, total_count):
        context = {
            "visitors": rows,
            "total_count": total_count,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Visitor Log Export",
            "columns": [
                {"name": "Visitor", "width": "15%"},
                {"name": "Student", "width": "15%"},
                {"name": "Purpose", "width": "20%"},
                {"name": "Entry", "width": "15%"},
                {"name": "Exit", "width": "15%"},
                {"name": "Recorded By", "width": "20%"},
            ]
        }

        pdf_bytes = render_to_pdf("hostel/export/visitor_logs_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            ws = workbook.add_worksheet("Visitor Logs")

            header_fmt = workbook.add_format({"bold": True, "bg_color": "#3b5998", "font_color": "white"})

            headers = [
                "Visitor Name", "Student Visited", "Purpose", "ID Proof", "ID Number",
                "Entry Time", "Exit Time", "Recorded By"
            ]

            for col, h in enumerate(headers):
                ws.write(0, col, h, header_fmt)

            for i, r in enumerate(rows, start=1):
                ws.write(i, 0, r['visitor_name'])
                ws.write(i, 1, r['student_visited'])
                ws.write(i, 2, r['purpose'])
                ws.write(i, 3, r['id_proof'])
                ws.write(i, 4, r['id_number'])
                ws.write(i, 5, r['entry_time'])
                ws.write(i, 6, r['exit_time'])
                ws.write(i, 7, r['recorded_by'])

            ws.set_column("A:H", 20)

            summary_row = len(rows) + 2
            ws.write(summary_row, 0, "Total Visitors:")
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


# views.py (add these classes)
class HostelVisitorLogListView( FinanceAccessRequiredMixin, ListView):
    model = HostelVisitorLog
    template_name = 'hostel/visitor_log/visitor_list.html'
    context_object_name = 'visitors'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelVisitorLog.objects.filter(institution=institution).select_related(
            'student_visited', 'recorded_by', 'student_visited__user'
        ).order_by('-entry_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Statistics
        today = timezone.now().date()
        context['total_visitors'] = HostelVisitorLog.objects.filter(institution=institution).count()
        context['today_visitors'] = HostelVisitorLog.objects.filter(
            institution=institution,
            entry_time__date=today
        ).count()
        context['active_visits'] = HostelVisitorLog.objects.filter(
            institution=institution,
            exit_time__isnull=True
        ).count()
        
        return context


class HostelVisitorLogCreateView( FinanceAccessRequiredMixin, CreateView):
    model = HostelVisitorLog
    form_class = HostelVisitorLogForm
    template_name = 'hostel/visitor_log/visitor_form.html'
    success_url = reverse_lazy('hostel:visitor_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request  # Ensure request is passed to form
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Visitor Entry'
        context['submit_text'] = 'Record Entry'
        return context
    
    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        form.instance.recorded_by = getattr(self.request.user, 'staff', None)
        messages.success(self.request, 'Visitor entry recorded successfully!')
        return super().form_valid(form)


class HostelVisitorLogUpdateView( FinanceAccessRequiredMixin, UpdateView):
    model = HostelVisitorLog
    form_class = HostelVisitorLogForm
    template_name = 'hostel/visitor_log/visitor_form.html'
    success_url = reverse_lazy('hostel:visitor_list')
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelVisitorLog.objects.filter(institution=institution)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request  # Ensure request is passed to form
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Visitor Entry'
        context['submit_text'] = 'Update Entry'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Visitor entry updated successfully!')
        return super().form_valid(form)


class HostelVisitorLogDeleteView( DirectorRequiredMixin, DeleteView):
    model = HostelVisitorLog
    template_name = 'hostel/visitor_log/visitor_confirm_delete.html'
    success_url = reverse_lazy('hostel:visitor_list')
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelVisitorLog.objects.filter(institution=institution)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Visitor entry deleted successfully!')
        return super().delete(request, *args, **kwargs)


class HostelVisitorLogExitView( FinanceAccessRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        visitor = get_object_or_404(
            HostelVisitorLog, 
            id=kwargs['pk'],
            institution=get_user_institution(request.user)
        )
        
        if visitor.exit_time is None:
            visitor.exit_time = timezone.now()
            visitor.save()
            messages.success(request, f'Exit time recorded for {visitor.visitor_name}')
        else:
            messages.warning(request, f'Exit already recorded for {visitor.visitor_name}')
        
        return redirect('hostel:visitor_list')