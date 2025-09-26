
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import timedelta
import csv
from .forms import ClassForm, SectionForm, TimetableForm
from django.utils import timezone
from django.conf import settings
import os
from .models import House,AcademicYear
from apps.organization.models import Institution
from utils.utils import render_to_pdf, export_pdf_response
from io import StringIO



def export_houses(request):
    """
    Export Houses as CSV or PDF.
    GET params:
      - format: 'csv' or 'pdf' (default 'csv')
      - columns: multiple columns via ?columns=name&columns=color (or single csv string depending on form)
    """

    fmt = request.GET.get("format", "csv").lower()
    # Accept both repeated parameters and comma-separated style
    columns = request.GET.getlist("columns")
    if not columns:
        # maybe single comma-separated param
        columns_param = request.GET.get("columns", "")
        if columns_param:
            columns = [c.strip() for c in columns_param.split(",") if c.strip()]

    # default fields if none selected
    if not columns:
        columns = ["name", "color", "is_active", "created_at"]

    houses_qs = House.objects.all().order_by("name")

    # build rows as plain dicts and format values for easy template/csv usage
    rows = []
    for h in houses_qs:
        r = {}
        # always add requested keys if available
        if "name" in columns:
            r["name"] = h.name
        if "color" in columns:
            r["color"] = h.color or ""
        if "is_active" in columns:
            r["is_active"] = "Active" if h.is_active else "Inactive"
        if "created_at" in columns:
            r["created_at"] = h.created_at.strftime("%b %d, %Y") if h.created_at else ""
        if "description" in columns:
            r["description"] = (h.description[:200] + "...") if getattr(h, "description", None) else ""
        # any custom fields you want to support can be added here. e.g. captain, vice_captain
        # if "captain" in columns:
        #     r["captain"] = h.captain.get_full_name() if getattr(h, "captain", None) else ""
        rows.append(r)

    # CSV export
    if fmt == "csv":
        # Use StringIO for text CSV
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow([col.replace("_", " ").title() for col in columns])  # header
        for r in rows:
            writer.writerow([r.get(col, "") for col in columns])
        resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="houses.csv"'
        return resp

    # PDF export using your render_to_pdf util and a template
    if fmt == "pdf":
        organization = Institution.objects.first()
        context = {
            "columns": columns,
            "houses": rows,
            "generated_date": timezone.now(),
            # optional organization/logo values - adjust as per your project
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization else None,
        }

        pdf_bytes = render_to_pdf("academics/house/export_houses_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, "houses.pdf")
        return HttpResponse("Error generating PDF", status=500)

    # unsupported format
    return HttpResponse("Invalid export format", status=400)


class AcademicsBaseView:
    """Base class for academics views with common methods"""
    
    def get_institution(self):
        """Get institution from the logged-in user's profile."""
        user = self.request.user
        if hasattr(user, 'profile') and hasattr(user.profile, 'institution'):
            return user.profile.institution
        return None
    
    def get_current_academic_year(self):
        """Get current academic year for the institution."""
        institution = self.get_institution()
        if institution:
            try:
                return AcademicYear.objects.filter(
                    is_current=True, 
                    institution=institution
                ).first()
            except AcademicYear.DoesNotExist:
                return None
        return None
    
# ===== HOUSE VIEWS =====
class HouseListView(AcademicsBaseView, ListView):
    model = House
    template_name = 'academics/house/house_list.html'
    context_object_name = 'houses'

    def get_queryset(self):
        institution = self.get_institution()
        if institution:
            return House.objects.filter(institution=institution).order_by('name')
        return House.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = self.get_institution()
        if institution:
            context['active_houses_count'] = House.objects.filter(institution=institution, is_active=True).count()
            context['inactive_houses_count'] = House.objects.filter(institution=institution, is_active=False).count()
        return context


class HouseCreateView(AcademicsBaseView, CreateView):
    model = House
    fields = ['name', 'color', 'description', 'is_active']
    template_name = 'academics/house/house_form.html'
    success_url = reverse_lazy('academics:house_list')

    def form_valid(self, form):
        form.instance.institution = self.get_institution()
        response = super().form_valid(form)
        messages.success(self.request, f'House "{form.instance.name}" created successfully!')
        return response


class HouseUpdateView(AcademicsBaseView, UpdateView):
    model = House
    fields = ['name', 'color', 'description', 'is_active']
    template_name = 'academics/house/house_form.html'
    success_url = reverse_lazy('academics:house_list')

    def get_queryset(self):
        return House.objects.filter(institution=self.get_institution())

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'House "{form.instance.name}" updated successfully!')
        return response


class HouseDeleteView(AcademicsBaseView, DeleteView):
    model = House
    template_name = 'academics/house/house_confirm_delete.html'
    success_url = reverse_lazy('academics:house_list')

    def get_queryset(self):
        return House.objects.filter(institution=self.get_institution())

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'House deleted successfully!')
        return super().delete(request, *args, **kwargs)


