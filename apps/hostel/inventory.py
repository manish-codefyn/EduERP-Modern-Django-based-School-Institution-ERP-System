from datetime import datetime
from io import StringIO, BytesIO
import csv
import xlsxwriter
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.utils import timezone

from apps.core.utils import get_user_institution
from .models import HostelInventory, Hostel
from .forms import HostelInventoryForm
from utils.utils import render_to_pdf, export_pdf_response  # Ensure these exist


class HostelInventoryListView(LoginRequiredMixin, ListView):
    model = HostelInventory
    template_name = 'hostel/inventory/inventory_list.html'
    context_object_name = 'inventory_items'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = HostelInventory.objects.select_related('hostel', 'institution')
        
        # Filter by hostel if provided
        hostel_id = self.request.GET.get('hostel')
        if hostel_id:
            queryset = queryset.filter(hostel_id=hostel_id)
        
        # Filter by condition if provided
        condition = self.request.GET.get('condition')
        if condition:
            queryset = queryset.filter(condition=condition)
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(item_name__icontains=search_query) |
                Q(notes__icontains=search_query)
            )
        
        return queryset.order_by('item_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hostels'] = Hostel.objects.all()
        context['conditions'] = dict(HostelInventory._meta.get_field('condition').choices)
        return context

class HostelInventoryDetailView(LoginRequiredMixin, DetailView):
    model = HostelInventory
    template_name = 'hostel/inventory/inventory_detail.html'
    context_object_name = 'item'

class HostelInventoryCreateView(LoginRequiredMixin, CreateView):
    model = HostelInventory
    form_class = HostelInventoryForm
    template_name = 'hostel/inventory/inventory_form.html'
    
    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, 'Inventory item created successfully!')
        return super().form_valid(form)


class HostelInventoryUpdateView(LoginRequiredMixin, UpdateView):
    model = HostelInventory
    form_class = HostelInventoryForm
    template_name = 'hostel/inventory/inventory_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Inventory item updated successfully!')
        return super().form_valid(form)



class HostelInventoryDeleteView(LoginRequiredMixin, DeleteView):
    model = HostelInventory
    template_name = 'hostel/inventory/inventory_confirm_delete.html'
    success_url = reverse_lazy('hostel:inventory_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Inventory item deleted successfully!')
        return super().delete(request, *args, **kwargs)


class HostelInventoryExportView(LoginRequiredMixin, View):
    """
    Export Hostel Inventory data in CSV, PDF, Excel formats
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        hostel_id = request.GET.get("hostel")
        condition = request.GET.get("condition")

        # Filter queryset
        qs = HostelInventory.objects.select_related('hostel', 'institution')
        if hostel_id:
            qs = qs.filter(hostel_id=hostel_id)
        if condition:
            qs = qs.filter(condition=condition)

        # Prepare filename
        filename_parts = ["hostel_inventory"]
        if hostel_id:
            filename_parts.append(f"hostel_{hostel_id}")
        if condition:
            filename_parts.append(f"condition_{condition}")
        filename = "_".join(filename_parts).lower() + f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Prepare rows
        rows = []
        for item in qs:
            rows.append({
                "hostel": item.hostel.name,
                "institution": item.institution.name,
                "item_name": item.item_name,
                "quantity": item.quantity,
                "condition": item.get_condition_display(),
                "last_maintenance": item.last_maintenance.strftime("%Y-%m-%d") if item.last_maintenance else "-",
                "next_maintenance": item.next_maintenance.strftime("%Y-%m-%d") if item.next_maintenance else "-",
                "notes": item.notes or "-",
            })

        if fmt == "csv":
            return self.export_csv(rows, filename)
        elif fmt == "pdf":
            return self.export_pdf(rows, filename)
        elif fmt == "excel":
            return self.export_excel(rows, filename)
        else:
            return HttpResponse("Invalid format. Use csv, pdf, excel.", status=400)

    def export_csv(self, rows, filename):
        buffer = StringIO()
        writer = csv.writer(buffer)

        writer.writerow([
            "Hostel", "Institution", "Item Name", "Quantity",
            "Condition", "Last Maintenance", "Next Maintenance", "Notes"
        ])

        for r in rows:
            writer.writerow([
                r['hostel'], r['institution'], r['item_name'], r['quantity'],
                r['condition'], r['last_maintenance'], r['next_maintenance'], r['notes']
            ])

        writer.writerow([])
        writer.writerow(["Total Items:", len(rows)])
        writer.writerow(["Export Date:", timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_pdf(self, rows, filename):
        organization = get_user_institution(self.request.user)
        context = {
            "items": rows,
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "total_count": len(rows),
            "export_date": timezone.now(),
            "title": "Hostel Inventory Export",
            "columns": [
                {"name": "Hostel", "width": "15%"},
                {"name": "Institution", "width": "15%"},
                {"name": "Item Name", "width": "15%"},
                {"name": "Quantity", "width": "8%"},
                {"name": "Condition", "width": "10%"},
                {"name": "Last Maintenance", "width": "12%"},
                {"name": "Next Maintenance", "width": "12%"},
                {"name": "Notes", "width": "15%"},
            ]
        }

        pdf_bytes = render_to_pdf("hostel/export/hostel_inventory_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

    def export_excel(self, rows, filename):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            ws = workbook.add_worksheet("Hostel Inventory")
            header_fmt = workbook.add_format({"bold": True, "bg_color": "#3b5998", "font_color": "white"})

            headers = ["Hostel", "Institution", "Item Name", "Quantity",
                       "Condition", "Last Maintenance", "Next Maintenance", "Notes"]
            for col, h in enumerate(headers):
                ws.write(0, col, h, header_fmt)

            for i, r in enumerate(rows, start=1):
                ws.write(i, 0, r['hostel'])
                ws.write(i, 1, r['institution'])
                ws.write(i, 2, r['item_name'])
                ws.write(i, 3, r['quantity'])
                ws.write(i, 4, r['condition'])
                ws.write(i, 5, r['last_maintenance'])
                ws.write(i, 6, r['next_maintenance'])
                ws.write(i, 7, r['notes'])

            ws.set_column("A:H", 20)
            summary_row = len(rows) + 2
            ws.write(summary_row, 0, "Total Items:")
            ws.write(summary_row, 1, len(rows))
            ws.write(summary_row + 1, 0, "Export Date:")
            ws.write(summary_row + 1, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response
