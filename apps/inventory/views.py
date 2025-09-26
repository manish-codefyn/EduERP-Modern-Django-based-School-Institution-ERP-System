import csv
from io import StringIO, BytesIO
from datetime import datetime, timedelta,date
import xlsxwriter
from django.http import HttpResponse,JsonResponse
from django.utils import timezone
from django.db.models import Count, Q, Sum, Case, When, IntegerField
from django.db import models
from django.views.decorators.http import require_GET    
from utils.utils import render_to_pdf, export_pdf_response
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import StaffManagementRequiredMixin
from .models import ItemCategory, Item, PurchaseOrder, StockTransaction
from .forms import (ItemCategoryForm, ItemForm, PurchaseOrderForm, StockTransactionForm,
                    PurchaseOrderItemForm,PurchaseOrderStatusForm, InventoryFilterForm,PurchaseOrderItemFormSet)
from apps.core.utils import get_user_institution

# Dashboard View
class InventoryDashboardView(StaffManagementRequiredMixin, TemplateView):
    template_name = 'inventory/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Basic statistics
        total_items = Item.objects.filter(institution=institution).count()
        total_categories = ItemCategory.objects.filter(institution=institution, is_active=True).count()
        
        # Stock status breakdown
        stock_status = Item.objects.filter(institution=institution).aggregate(
            total_value=Sum(models.F('quantity') * models.F('price'), output_field=models.DecimalField()),
            in_stock=Count('id', filter=Q(quantity__gt=models.F('min_quantity'))),
            low_stock=Count('id', filter=Q(quantity__lte=models.F('min_quantity')) & Q(quantity__gt=0)),
            out_of_stock=Count('id', filter=Q(quantity__lte=0))
        )
        
        # Recent transactions
        recent_transactions = StockTransaction.objects.filter(
            institution=institution
        ).select_related('item', 'performed_by').order_by('-transaction_date')[:10]
        
        # Purchase order statistics
        po_stats = PurchaseOrder.objects.filter(institution=institution).aggregate(
            total_orders=Count('id'),
            pending_orders=Count('id', filter=Q(status__in=['draft', 'submitted', 'approved', 'ordered'])),
            received_orders=Count('id', filter=Q(status='received'))
        )
        
        # Low stock items
        low_stock_items = Item.objects.filter(
            institution=institution,
            quantity__lte=models.F('min_quantity')
        ).order_by('quantity')[:5]
        
        # Monthly transaction chart data
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_data = StockTransaction.objects.filter(
            institution=institution,
            transaction_date__gte=six_months_ago
        ).extra({
            'month': "EXTRACT(month FROM transaction_date)",
            'year': "EXTRACT(year FROM transaction_date)"
        }).values('year', 'month').annotate(
            total_quantity=Sum('quantity'),
            transaction_count=Count('id')
        ).order_by('year', 'month')
        
        context.update({
            'total_items': total_items,
            'total_categories': total_categories,
            'total_value': stock_status['total_value'] or 0,
            'in_stock_count': stock_status['in_stock'] or 0,
            'low_stock_count': stock_status['low_stock'] or 0,
            'out_of_stock_count': stock_status['out_of_stock'] or 0,
            'recent_transactions': recent_transactions,
            'total_orders': po_stats['total_orders'] or 0,
            'pending_orders': po_stats['pending_orders'] or 0,
            'received_orders': po_stats['received_orders'] or 0,
            'low_stock_items': low_stock_items,
            # 'monthly_data': list(monthly_data),
        })
        return context


# Item Category Views
class ItemCategoryListView( StaffManagementRequiredMixin, ListView):
    model = ItemCategory
    template_name = 'inventory/category/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return ItemCategory.objects.filter(institution=institution)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        stats = ItemCategory.objects.filter(institution=institution).aggregate(
            total_categories=Count('id'),
            active_categories=Count('id', filter=Q(is_active=True)),
            items_per_category=Count('item', distinct=True)
        )
        
        context.update({
            "total_categories": stats["total_categories"],
            "active_categories": stats["active_categories"],
        })
        return context

class ItemCategoryCreateView( StaffManagementRequiredMixin, CreateView):
    model = ItemCategory
    form_class = ItemCategoryForm
    template_name = 'inventory/category/category_form.html'

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, "Category created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('inventory:category_list')

class ItemCategoryUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = ItemCategory
    form_class = ItemCategoryForm
    template_name = 'inventory/category/category_form.html'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return ItemCategory.objects.filter(institution=institution)

    def form_valid(self, form):
        messages.success(self.request, "Category updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('inventory:category_list')

class ItemCategoryDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = ItemCategory
    template_name = 'inventory/category/category_confirm_delete.html'
    success_url = reverse_lazy('inventory:category_list')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return ItemCategory.objects.filter(institution=institution)

# Item Views
class ItemListView( StaffManagementRequiredMixin, ListView):
    model = Item
    template_name = 'inventory/items/item_list.html'
    context_object_name = 'items'
    paginate_by = 20

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = Item.objects.filter(institution=institution).select_related('category')

        # Apply filters
        form = InventoryFilterForm(self.request.GET, institution=institution)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            category = form.cleaned_data.get('category')
            status = form.cleaned_data.get('status')

            if search:
                queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
            if category:
                queryset = queryset.filter(category=category)
            if status:
                if status == 'in_stock':
                    queryset = queryset.filter(quantity__gt=models.F('min_quantity'))
                elif status == 'low_stock':
                    queryset = queryset.filter(quantity__lte=models.F('min_quantity'), quantity__gt=0)
                elif status == 'out_of_stock':
                    queryset = queryset.filter(quantity__lte=0)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Statistics
        stats = Item.objects.filter(institution=institution).aggregate(
            total_items=Count('id'),
            total_value=Sum(models.F('quantity') * models.F('price')),
            low_stock=Count('id', filter=Q(quantity__lte=models.F('min_quantity')) & Q(quantity__gt=0)),
            out_of_stock=Count('id', filter=Q(quantity__lte=0))
        )
        
        context['filter_form'] = InventoryFilterForm(self.request.GET, institution=institution)
        context.update(stats)
        return context

class ItemCreateView( StaffManagementRequiredMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = 'inventory/items/item_form.html'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        institution = get_user_institution(self.request.user)
        form.fields['category'].queryset = ItemCategory.objects.filter(institution=institution, is_active=True)
        return form

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, "Item created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('inventory:item_list')

class ItemUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = Item
    form_class = ItemForm
    template_name = 'inventory/items/item_form.html'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Item.objects.filter(institution=institution)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        institution = get_user_institution(self.request.user)
        form.fields['category'].queryset = ItemCategory.objects.filter(institution=institution, is_active=True)
        return form

    def form_valid(self, form):
        messages.success(self.request, "Item updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('inventory:item_list')

class ItemDetailView( StaffManagementRequiredMixin, DetailView):
    model = Item
    template_name = 'inventory/items/item_detail.html'
    context_object_name = 'item'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Item.objects.filter(institution=institution)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transactions'] = StockTransaction.objects.filter(
            item=self.object
        ).select_related('performed_by').order_by('-transaction_date')[:20]
        return context

class ItemDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = Item
    template_name = 'inventory/items/item_confirm_delete.html'
    context_object_name = 'item'
    success_url = reverse_lazy('inventory:item_list')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Item.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        item_name = self.object.name
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Item "{item_name}" has been deleted successfully.')
        return response

# Stock Transaction Views
class StockTransactionCreateView( StaffManagementRequiredMixin, CreateView):
    model = StockTransaction
    form_class = StockTransactionForm
    template_name = 'inventory/stocks/transaction_form.html'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        institution = get_user_institution(self.request.user)
        form.fields['item'].queryset = Item.objects.filter(institution=institution)
        return form

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        form.instance.performed_by = self.request.user
        messages.success(self.request, "Stock transaction completed successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('inventory:item_list')

# Export Views
class InventoryExportView( StaffManagementRequiredMixin, ListView):
    model = Item
    context_object_name = "items"

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Item.objects.select_related('category').filter(institution=institution)

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "csv").lower()
        queryset = self.get_queryset()

        filename = f"inventory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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

        writer.writerow(['Item Name', 'Category', 'Quantity', 'Min Quantity', 'Unit', 'Price', 'Location', 'Status'])

        for item in queryset:
            writer.writerow([
                item.name,
                item.category.name,
                item.quantity,
                item.min_quantity,
                item.unit,
                item.price or '0.00',
                item.location,
                item.status.replace('_', ' ').title()
            ])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, queryset, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Inventory")

            header_format = workbook.add_format({
                "bold": True, "bg_color": "#2c3e50", "font_color": "white",
                "border": 1, "align": "center", "valign": "vcenter"
            })

            headers = ['Item Name', 'Category', 'Quantity', 'Min Quantity', 'Unit', 'Price', 'Location', 'Status']
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, item in enumerate(queryset, start=1):
                worksheet.write(row_idx, 0, item.name)
                worksheet.write(row_idx, 1, item.category.name)
                worksheet.write(row_idx, 2, item.quantity)
                worksheet.write(row_idx, 3, item.min_quantity)
                worksheet.write(row_idx, 4, item.unit)
                worksheet.write(row_idx, 5, float(item.price or 0))
                worksheet.write(row_idx, 6, item.location)
                worksheet.write(row_idx, 7, item.status.replace('_', ' ').title())

            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:B', 20)
            worksheet.set_column('C:D', 15)
            worksheet.set_column('E:E', 10)
            worksheet.set_column('F:F', 12)
            worksheet.set_column('G:G', 20)
            worksheet.set_column('H:H', 15)

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, queryset, filename, organization):
        context = {
            "items": queryset,
            "total_count": queryset.count(),
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Inventory Export",
        }
        pdf_bytes = render_to_pdf("inventory/export/inventory_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)
    

# Stock Transaction Views
class StockTransactionListView( StaffManagementRequiredMixin, ListView):
    model = StockTransaction
    template_name = 'inventory/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return StockTransaction.objects.filter(
            institution=institution
        ).select_related('item', 'performed_by').order_by('-transaction_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()

        # Stats
        context['total_transactions'] = qs.count()
        context['total_purchases'] = qs.filter(transaction_type='purchase').count()
        context['total_issues'] = qs.filter(transaction_type='issue').count()
        context['total_returns'] = qs.filter(transaction_type='return').count()
        context['total_damages'] = qs.filter(transaction_type='damage').count()
        context['total_adjustments'] = qs.filter(transaction_type='adjustment').count()
        
        return context

class StockTransactionCreateView( StaffManagementRequiredMixin, CreateView):
    model = StockTransaction
    form_class = StockTransactionForm
    template_name = 'inventory/transaction_form.html'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        institution = get_user_institution(self.request.user)
        form.fields['item'].queryset = Item.objects.filter(institution=institution)
        return form

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        form.instance.performed_by = self.request.user
        messages.success(self.request, "Stock transaction completed successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('inventory:transaction_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['institution'] = get_user_institution(self.request.user)
        return kwargs

class StockTransactionDetailView( StaffManagementRequiredMixin, DetailView):
    model = StockTransaction
    template_name = 'inventory/transaction_detail.html'
    context_object_name = 'transaction'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return StockTransaction.objects.filter(institution=institution)

# Purchase Order Views
class PurchaseOrderListView( StaffManagementRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_list.html'
    context_object_name = 'purchase_orders'
    paginate_by = 20
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = PurchaseOrder.objects.filter(
            institution=institution
        ).select_related('created_by', 'approved_by').order_by('-created_at')
        
        # Apply filters
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if search:
            queryset = queryset.filter(
                Q(po_number__icontains=search) |
                Q(supplier__icontains=search) |
                Q(notes__icontains=search)
            )
        
        if status:
            queryset = queryset.filter(status=status)
            
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
            
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Get all POs for statistics
        all_pos = PurchaseOrder.objects.filter(institution=institution)
        
        # Statistics
        context['total_count'] = all_pos.count()
        context['draft_count'] = all_pos.filter(status='draft').count()
        context['pending_count'] = all_pos.filter(status__in=['submitted']).count()
        context['approved_count'] = all_pos.filter(status='approved').count()
        context['ordered_count'] = all_pos.filter(status='ordered').count()
        context['issues_count'] = all_pos.filter(status__in=['rejected', 'cancelled']).count()
        
        # Dates for overdue calculations
        from datetime import date, timedelta
        context['today'] = date.today()
        context['soon_date'] = date.today() + timedelta(days=7)
        
        return context
    
class PurchaseOrderCreateView( StaffManagementRequiredMixin, CreateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'inventory/purchase_order_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        if self.request.POST:
            context['formset'] = PurchaseOrderItemFormSet(
                self.request.POST,
                instance=self.object,
                form_kwargs={'institution': institution}
            )
        else:
            context['formset'] = PurchaseOrderItemFormSet(
                instance=self.object,
                form_kwargs={'institution': institution}
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            # Set additional fields
            form.instance.institution = get_user_institution(self.request.user)
            form.instance.created_by = self.request.user
            
            # Handle status based on which button was clicked
            if 'submit_po' in self.request.POST:
                form.instance.status = 'submitted'
            
            response = super().form_valid(form)
            
            # Save formset
            formset.instance = self.object
            formset.save()
            
            messages.success(self.request, "Purchase order created successfully.")
            return response
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        # Redirect to the detail page of the newly created purchase order
        return reverse('inventory:purchase_order_detail', kwargs={'pk': self.object.pk})


class PurchaseOrderUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'inventory/purchase_order_form.html'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return PurchaseOrder.objects.filter(institution=institution)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        if self.request.POST:
            context['formset'] = PurchaseOrderItemFormSet(
                self.request.POST,
                instance=self.object,
                form_kwargs={'institution': institution}
            )
        else:
            context['formset'] = PurchaseOrderItemFormSet(
                instance=self.object,
                form_kwargs={'institution': institution}
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            # Handle status based on which button was clicked
            if 'submit_po' in self.request.POST and self.object.status == 'draft':
                form.instance.status = 'submitted'
            
            response = super().form_valid(form)
            formset.save()
            
            messages.success(self.request, "Purchase order updated successfully.")
            return response
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        # Redirect to purchase order detail page after update
        return reverse('inventory:purchase_order_detail', kwargs={'pk': self.object.pk})


class PurchaseOrderDetailView( StaffManagementRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_detail.html'
    context_object_name = 'purchase_order'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return PurchaseOrder.objects.filter(institution=institution)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        purchase_order = self.object
        
        # Calculate additional statistics
        items = purchase_order.items.all()
        context['total_quantity'] = items.aggregate(total=Sum('quantity'))['total'] or 0
        context['average_price'] = purchase_order.total_amount / items.count() if items.count() > 0 else 0
        
        # Dates for timeline
        context['today'] = date.today()
        context['soon_date'] = date.today() + timedelta(days=7)
        
        return context

@require_GET
def get_item_price(request, pk):
    institution = get_user_institution(request.user)
    item = get_object_or_404(Item, pk=pk, institution=institution)
    return JsonResponse({'price': str(item.price or 0)})
       
class PurchaseOrderStatusUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = PurchaseOrder
    form_class = PurchaseOrderStatusForm
    template_name = 'inventory/purchase_order_status_form.html'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return PurchaseOrder.objects.filter(institution=institution)
    
    def form_valid(self, form):
        status = form.cleaned_data['status']
        reason_notes = form.cleaned_data.get('reason_notes')
        order_date = form.cleaned_data.get('order_date')
        
        # Handle additional fields
        if status == 'approved' and not form.instance.approved_by:
            form.instance.approved_by = self.request.user
        
        if order_date and status == 'ordered':
            form.instance.order_date = order_date
            
        # Add reason to notes if provided
        if reason_notes and status in ['rejected', 'cancelled']:
            current_notes = form.instance.notes or ''
            reason_text = f"\n\n--- {status.upper()} REASON ---\n{reason_notes}"
            form.instance.notes = current_notes + reason_text
        
        # If status is received, create stock transactions
        if status == 'received':
            self.create_stock_transactions(form.instance)
        
        messages.success(self.request, f"Purchase order status updated to {form.instance.get_status_display()}.")
        return super().form_valid(form)
    
    def create_stock_transactions(self, purchase_order):
        """Create stock transactions for received items"""
        for item in purchase_order.items.all():
            StockTransaction.objects.create(
                institution=purchase_order.institution,
                item=item.item,
                transaction_type='purchase',
                quantity=item.quantity,
                reference=f"PO-{purchase_order.po_number}",
                notes=f"Received from purchase order {purchase_order.po_number}",
                performed_by=self.request.user
            )
    
    def get_success_url(self):
        return reverse('inventory:purchase_order_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the detail URL to the context
        context['detail_url'] = reverse('inventory:purchase_order_detail', kwargs={'pk': self.object.pk})
        return context

class PurchaseOrderDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_confirm_delete.html'
    context_object_name = 'purchase_order'
    success_url = reverse_lazy('inventory:purchase_order_list')  # Replace with your PO list view URL

    def get_queryset(self):
        """Ensure the user can only delete PurchaseOrders from their institution."""
        institution = get_user_institution(self.request.user)
        return PurchaseOrder.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        """Add a success message after deletion."""
        messages.success(request, "Purchase order deleted successfully.")
        return super().delete(request, *args, **kwargs)
# API View
@require_GET
def get_item_quantity(request, pk):
    institution = get_user_institution(request.user)
    item = get_object_or_404(Item, pk=pk, institution=institution)
    return JsonResponse({'quantity': item.quantity})