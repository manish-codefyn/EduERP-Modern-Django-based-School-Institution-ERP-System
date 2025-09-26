# finance/views.py
import csv
from io import StringIO
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from .models import FeeStructure,FeeInvoice,Payment
from apps.academics.models import AcademicYear, Class
from apps.students.models import Student
from utils.utils import render_to_pdf, export_pdf_response
from apps.core.mixins import FinanceAccessRequiredMixin
from apps.core.permissions import RoleBasedPermissionMixin
from apps.core.utils import get_user_institution 
from decimal import Decimal



class PaymentDetailExportView(View):
    """
    Export single Payment details by ID
    Supports CSV, Excel, and PDF formats
    """

    def get(self, request, pk, *args, **kwargs):
        fmt = request.GET.get("format", "pdf").lower()  # default PDF

        # Get user's institution
        institution = get_user_institution(request.user, request)
        if not institution:
            return HttpResponse("No institution associated with your account", status=400)

        # Get the payment and ensure it belongs to the user's institution
        payment = get_object_or_404(Payment, pk=pk, institution=institution)

        # Build row data
        data = {
            "Payment Number": payment.payment_number,
            "Student Name": payment.student.full_name if payment.student else "N/A",
            "Roll Number": payment.student.roll_number if payment.student else "N/A",
            "Class": str(payment.student.current_class) if payment.student and payment.student.current_class else "N/A",
            "Academic Year": str(payment.invoice.academic_year) if payment.invoice and payment.invoice.academic_year else "N/A",
            "Invoice Number": payment.invoice.invoice_number if payment.invoice else "N/A",
            "Payment Date": payment.payment_date.strftime("%d-%m-%y") if payment.payment_date else "N/A",
            "Payment Mode": payment.get_payment_mode_display(),
            "Reference Number": payment.reference_number or "N/A",
            "Total Amount": f"{payment.amount:.2f}",
            "Amount Paid": f"{payment.amount_paid:.2f}",
            "Balance": f"{payment.amount - payment.amount_paid:.2f}",
            "Status": payment.get_status_display(),
            "Remarks": payment.remarks or "N/A",
        }

        # CSV / Excel export
        if fmt in ["csv", "excel"]:
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(data.keys())
            writer.writerow(data.values())

            resp = HttpResponse(buffer.getvalue(),
                                content_type="application/vnd.ms-excel" if fmt=="excel" else "text/csv")
            resp["Content-Disposition"] = f'attachment; filename="Payment_{payment.payment_number}.{ "xls" if fmt=="excel" else "csv" }"'
            return resp

        # PDF export
        elif fmt == "pdf":
            context = {
                "payment": data,
                "student_name": payment.student.full_name if payment.student else "N/A",
                "reference_number": payment.reference_number if payment else "N/A",
                "amount_paid": payment.amount_paid if payment else "N/A",
                "student_father": payment.student.father if payment.student else "N/A",
                "student_address": payment.student.permanent_address if payment.student else "N/A",
                "generated_date": timezone.now(),
                "organization": institution,
                "logo": getattr(institution.logo, 'url', None) if institution.logo else None,
                "stamp": getattr(institution.stamp, 'url', None) if institution.stamp  else None,
            }
            pdf_bytes = render_to_pdf("finance/export/payment_detail_pdf.html", context)
            if pdf_bytes:
                return export_pdf_response(pdf_bytes, f"Payment_{payment.payment_number}.pdf")
            return HttpResponse("Error generating PDF", status=500)

        return HttpResponse("Invalid export format", status=400)


class PaymentExportView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, View):
    """
    Export Payment data with filters and totals calculation
    """
    permission_required = 'finance.view_payment'

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        payment_status = request.GET.get("payment_status")
        class_id = request.GET.get("class_id")
        academic_year_id = request.GET.get("academic_year_id")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        # Base queryset filtered by user's institution
        institution = get_user_institution(request.user, request)
        if not institution:
            return HttpResponse("No institution associated with your account", status=400)
        
        payments_qs = Payment.objects.filter(institution=institution)

        # Apply filters
        filters = Q()

        if payment_status:
            filters &= Q(status=payment_status)
            
        if class_id:
            filters &= Q(student__current_class_id=class_id)
            class_obj = get_object_or_404(Class, id=class_id, institution=institution)
        else:
            class_obj = None

        if academic_year_id:
            filters &= Q(invoice__academic_year_id=academic_year_id)
            academic_year_obj = get_object_or_404(AcademicYear, id=academic_year_id, institution=institution)
        else:
            academic_year_obj = None

        # Date range filter
        if start_date:
            filters &= Q(payment_date__gte=start_date)
        if end_date:
            filters &= Q(payment_date__lte=end_date)

        payments_qs = payments_qs.filter(filters).select_related(
            'student', 'student__current_class', 'invoice__academic_year', 'invoice'
        ).order_by('-payment_date', 'student__roll_number')

        # Build filename
        filename_parts = ["payments"]
        if payment_status:
            filename_parts.append(f"Status_{payment_status}")
        if class_obj:
            filename_parts.append(f"Class_{class_obj.name}")
        if academic_year_obj:
            filename_parts.append(f"Year_{academic_year_obj.name}")
        if start_date:
            filename_parts.append(f"From_{start_date}")
        if end_date:
            filename_parts.append(f"To_{end_date}")

        filename = "_".join(filename_parts)

        # Build data rows and calculate totals
        rows = []
        total_amount = Decimal('0.00')
        total_paid = Decimal('0.00')
        total_balance = Decimal('0.00')
        
        for payment in payments_qs:
            row_data = {
                "payment_number": payment.payment_number,
                "student_name": payment.student.full_name if payment.student else "N/A",
                "roll_number": payment.student.roll_number if payment.student else "N/A",
                "class_name": str(payment.student.current_class) if payment.student and payment.student.current_class else "N/A",
                "academic_year": str(payment.invoice.academic_year) if payment.invoice and payment.invoice.academic_year else "N/A",
                "invoice_number": payment.invoice.invoice_number if payment.invoice else "N/A",
                "payment_date": payment.payment_date.strftime("%Y-%m-%d") if payment.payment_date else "N/A",
                "payment_mode": payment.get_payment_mode_display(),
                "reference_number": payment.reference_number or "N/A",
                "total_amount": f"{payment.amount:.2f}",
                "amount_paid": f"{payment.amount_paid:.2f}",
                "balance": f"{(payment.amount - payment.amount_paid):.2f}",
                "status": payment.get_status_display(),
                "remarks": payment.remarks or "N/A",
                "raw_amount": payment.amount,
                "raw_amount_paid": payment.amount_paid,
                "raw_balance": payment.amount - payment.amount_paid,
            }
            
            # Add to totals
            total_amount += payment.amount
            total_paid += payment.amount_paid
            total_balance += (payment.amount - payment.amount_paid)
            
            rows.append(row_data)

        # Handle empty results
        if not rows:
            if fmt == "pdf":
                context = {
                    "payments": [],
                    "generated_date": timezone.now(),
                    "payment_status_filter": payment_status,
                    "class_obj": class_obj,
                    "academic_year_obj": academic_year_obj,
                    "start_date": start_date,
                    "end_date": end_date,
                    "no_data": True,
                    "organization": institution,
                    "total_amount": 0,
                    "total_paid": 0,
                    "total_balance": 0,
                }
                pdf_bytes = render_to_pdf("finance/export/payments_pdf.html", context)
                if pdf_bytes:
                    return export_pdf_response(pdf_bytes, f"{filename}.pdf")
                return HttpResponse("Error generating PDF", status=500)
            else:
                return HttpResponse("No data found for the selected filters", status=404)

        # CSV Export
        if fmt == "csv":
            buffer = StringIO()
            writer = csv.writer(buffer)
            
            # Create headers
            headers = [
                "Payment Number", "Student Name", "Roll Number", "Class", 
                "Academic Year", "Invoice Number", "Payment Date", "Payment Mode",
                "Reference Number", "Total Amount", "Amount Paid", "Balance",
                "Status", "Remarks"
            ]
                
            writer.writerow(headers)
            
            for r in rows:
                row_values = [
                    r["payment_number"], r["student_name"], r["roll_number"],
                    r["class_name"], r["academic_year"], r["invoice_number"],
                    r["payment_date"], r["payment_mode"], r["reference_number"],
                    r["total_amount"], r["amount_paid"], r["balance"],
                    r["status"], r["remarks"]
                ]
                    
                writer.writerow(row_values)
            
            # Add totals row
            writer.writerow([])
            writer.writerow(["TOTALS", "", "", "", "", "", "", "", "", 
                           f"{total_amount:.2f}", f"{total_paid:.2f}", f"{total_balance:.2f}", "", ""])
                
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            return resp

        # PDF Export
        elif fmt == "pdf":
            context = {
                "payments": rows,
                "generated_date": timezone.now(),
                "payment_status_filter": payment_status,
                "class_obj": class_obj,
                "academic_year_obj": academic_year_obj,
                "start_date": start_date,
                "end_date": end_date,
                "organization": institution,
                "logo": getattr(institution.logo, 'url', None) if institution else None,
                "stamp": getattr(institution.stamp, 'url', None) if institution else None,
                "total_amount": total_amount,
                "total_paid": total_paid,
                "total_balance": total_balance,
                "filters_applied": any([payment_status, class_obj, academic_year_obj, start_date, end_date]),
            }
            pdf_bytes = render_to_pdf("finance/export/payments_pdf.html", context)
            if pdf_bytes:
                return export_pdf_response(pdf_bytes, f"{filename}.pdf")
            return HttpResponse("Error generating PDF", status=500)

        # Excel Export
        elif fmt == "excel":
            # For Excel export, return CSV with Excel content type
            buffer = StringIO()
            writer = csv.writer(buffer)
            
            headers = [
                "Payment Number", "Student Name", "Roll Number", "Class", 
                "Academic Year", "Invoice Number", "Payment Date", "Payment Mode",
                "Reference Number", "Total Amount", "Amount Paid", "Balance",
                "Status", "Remarks"
            ]
                
            writer.writerow(headers)
            
            for r in rows:
                row_values = [
                    r["payment_number"], r["student_name"], r["roll_number"],
                    r["class_name"], r["academic_year"], r["invoice_number"],
                    r["payment_date"], r["payment_mode"], r["reference_number"],
                    r["total_amount"], r["amount_paid"], r["balance"],
                    r["status"], r["remarks"]
                ]
                    
                writer.writerow(row_values)
            
            # Add totals row
            writer.writerow([])
            writer.writerow(["TOTALS", "", "", "", "", "", "", "", "", 
                           f"{total_amount:.2f}", f"{total_paid:.2f}", f"{total_balance:.2f}", "", ""])
                
            resp = HttpResponse(buffer.getvalue(), content_type="application/vnd.ms-excel")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.xls"'
            return resp

        return HttpResponse("Invalid export format", status=400)

class FeeInvoiceExportView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, View):
    """
    Export Fee Invoice data with filters:
    - status: Filter by invoice status
    - student_id: Filter by student
    - start_date, end_date: Filter by date range
    - Only for invoices in the user's institution
    """
    permission_required = 'finance.view_feeinvoice'

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        status = request.GET.get("status")
        student_id = request.GET.get("student")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        include_balance = request.GET.get("include_balance", "true") == "true"

        # Base queryset filtered by user's institution
        institution = getattr(request.user.profile, "institution", None)
        if not institution:
            return HttpResponse("No institution associated with your account", status=400)
        
        invoices_qs = FeeInvoice.objects.filter(institution=institution)

        # Apply filters
        filters = Q()

        if status:
            filters &= Q(status=status)
            
        if student_id:
            filters &= Q(student_id=student_id)
            student_obj = get_object_or_404(Student, id=student_id, institution=institution)
        else:
            student_obj = None

        if start_date and end_date:
            filters &= Q(issue_date__range=[start_date, end_date])
        elif start_date:
            filters &= Q(issue_date__gte=start_date)
        elif end_date:
            filters &= Q(issue_date__lte=end_date)

        invoices_qs = invoices_qs.filter(filters).select_related(
            'student', 'student__current_class', 'academic_year'
        ).order_by('-issue_date', 'student__roll_number')

        # Build filename
        filename_parts = ["fee_invoices"]
        if status:
            filename_parts.append(f"Status_{status}")
        if student_obj:
            filename_parts.append(f"Student_{student_obj.roll_number}")
        if start_date:
            filename_parts.append(f"From_{start_date}")
        if end_date:
            filename_parts.append(f"To_{end_date}")

        filename = "_".join(filename_parts)

        # Build data rows
        rows = []
        for invoice in invoices_qs:
            row_data = {
                "invoice_number": invoice.invoice_number,
                "student_name": invoice.student.full_name,
                "roll_number": invoice.student.roll_number,
                "class_name": str(invoice.student.current_class),
                "academic_year": str(invoice.academic_year),
                "issue_date": invoice.issue_date.strftime("%Y-%m-%d"),
                "due_date": invoice.due_date.strftime("%Y-%m-%d"),
                "total_amount": f"{invoice.total_amount:.2f}",
                "paid_amount": f"{invoice.paid_amount:.2f}",
                "status": invoice.get_status_display(),
            }
            
            if include_balance:
                row_data["balance"] = f"{(invoice.total_amount - invoice.paid_amount):.2f}"
            
            rows.append(row_data)

        # Handle empty results
        if not rows:
            if fmt == "pdf":
                context = {
                    "invoices": [],
                    "generated_date": timezone.now(),
                    "status_filter": status,
                    "student_obj": student_obj,
                    "start_date": start_date,
                    "end_date": end_date,
                    "no_data": True,
                    "organization": institution,
                }
                pdf_bytes = render_to_pdf("finance/export/fee_invoices_pdf.html", context)
                if pdf_bytes:
                    return export_pdf_response(pdf_bytes, f"{filename}.pdf")
                return HttpResponse("Error generating PDF", status=500)
            else:
                return HttpResponse("No data found for the selected filters", status=404)

        # CSV Export
        if fmt == "csv":
            buffer = StringIO()
            writer = csv.writer(buffer)
            
            # Create headers
            headers = ["Invoice Number", "Student Name", "Roll Number", "Class", 
                      "Academic Year", "Issue Date", "Due Date", "Total Amount", 
                      "Paid Amount", "Status"]
            if include_balance:
                headers.append("Balance")
                
            writer.writerow(headers)
            
            for r in rows:
                row_values = [
                    r["invoice_number"], r["student_name"], r["roll_number"],
                    r["class_name"], r["academic_year"], r["issue_date"],
                    r["due_date"], r["total_amount"], r["paid_amount"], r["status"]
                ]
                if include_balance:
                    row_values.append(r["balance"])
                    
                writer.writerow(row_values)
                
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            return resp

        # PDF Export
        elif fmt == "pdf":
            context = {
                "invoices": rows,
                "generated_date": timezone.now(),
                "status_filter": status,
                "student_obj": student_obj,
                "start_date": start_date,
                "end_date": end_date,
                "include_balance": include_balance,
                "organization": institution,
                "logo": getattr(institution.logo, 'url', None) if institution else None,
                "stamp": getattr(institution.stamp, 'url', None) if institution else None,
            }
            pdf_bytes = render_to_pdf("finance/export/fee_invoices_pdf.html", context)
            if pdf_bytes:
                return export_pdf_response(pdf_bytes, f"{filename}.pdf")
            return HttpResponse("Error generating PDF", status=500)

        # Excel Export
        elif fmt == "excel":
            # For Excel export, return CSV with Excel content type
            buffer = StringIO()
            writer = csv.writer(buffer)
            
            headers = ["Invoice Number", "Student Name", "Roll Number", "Class", 
                      "Academic Year", "Issue Date", "Due Date", "Total Amount", 
                      "Paid Amount", "Status"]
            if include_balance:
                headers.append("Balance")
                
            writer.writerow(headers)
            
            for r in rows:
                row_values = [
                    r["invoice_number"], r["student_name"], r["roll_number"],
                    r["class_name"], r["academic_year"], r["issue_date"],
                    r["due_date"], r["total_amount"], r["paid_amount"], r["status"]
                ]
                if include_balance:
                    row_values.append(r["balance"])
                    
                writer.writerow(row_values)
                
            resp = HttpResponse(buffer.getvalue(), content_type="application/vnd.ms-excel")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.xls"'
            return resp

        return HttpResponse("Invalid export format", status=400)


class FeeInvoiceDetailExportView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, View):
    """
    Export Invoice detail view with modern template
    """
    permission_required = 'finance.view_feeinvoice'

    def get(self, request, pk, *args, **kwargs):
        fmt = request.GET.get("format", "pdf").lower()
        
        # Get invoice by ID with institution check
        institution = get_user_institution(request.user, request)
        if not institution:
            return HttpResponse("No institution associated with your account", status=400)
        
        try:
            invoice = FeeInvoice.objects.select_related(
                'student', 'student__current_class', 'academic_year', 'institution'
            ).get(id=pk, institution=institution)
        except FeeInvoice.DoesNotExist:
            return HttpResponse("Invoice not found", status=404)

        # Prepare invoice data
        invoice_data = {
            "invoice_number": invoice.invoice_number,
            "student_name": invoice.student.full_name,
            "roll_number": invoice.student.roll_number,
            "class_name": str(invoice.student.current_class),
            "academic_year": str(invoice.academic_year),
            "issue_date": invoice.issue_date.strftime("%Y-%m-%d"),
            "due_date": invoice.due_date.strftime("%Y-%m-%d"),
            "total_amount": f"{invoice.total_amount:.2f}",
            "paid_amount": f"{invoice.paid_amount:.2f}",
            "balance": f"{(invoice.total_amount - invoice.paid_amount):.2f}",
            "status": invoice.get_status_display(),
            "is_overdue": invoice.overdue,
            "days_overdue": (timezone.now().date() - invoice.due_date).days if invoice.overdue else 0,
        }

        # Build filename
        filename = f"Invoice_{invoice.invoice_number}"

        # PDF Export (default)
        if fmt == "pdf":
            context = {
                "invoice": invoice_data,
                "generated_date": timezone.now(),
                "organization": institution,
                "logo": getattr(institution.logo, 'url', None) if institution else None,
                "stamp": getattr(institution.stamp, 'url', None) if institution else None,
            }
            pdf_bytes = render_to_pdf("finance/export/fee_invoice_detail_pdf.html", context)
            if pdf_bytes:
                return export_pdf_response(pdf_bytes, f"{filename}.pdf")
            return HttpResponse("Error generating PDF", status=500)

        # CSV Export
        elif fmt == "csv":
            buffer = StringIO()
            writer = csv.writer(buffer)
            
            # Create headers
            headers = ["Field", "Value"]
            writer.writerow(headers)
            
            for key, value in invoice_data.items():
                writer.writerow([key.replace('_', ' ').title(), value])
                
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            return resp

        # Excel Export
        elif fmt == "excel":
            buffer = StringIO()
            writer = csv.writer(buffer)
            
            headers = ["Field", "Value"]
            writer.writerow(headers)
            
            for key, value in invoice_data.items():
                writer.writerow([key.replace('_', ' ').title(), value])
                
            resp = HttpResponse(buffer.getvalue(), content_type="application/vnd.ms-excel")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.xls"'
            return resp

        return HttpResponse("Invalid export format", status=400)
    
    
class FeeStructureExportView(FinanceAccessRequiredMixin,RoleBasedPermissionMixin, View):
    """
    Export Fee Structure data with filters:
    - class_id: Filter by class
    - academic_year_id: Filter by academic year
    - is_active: Filter by active status
    - Only for fee structures in the user's institution
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        class_id = request.GET.get("class_id")
        academic_year_id = request.GET.get("academic_year_id")
        is_active = request.GET.get("is_active")
        include_inactive = request.GET.get("include_inactive") == "true"

        # Base queryset filtered by user's institution
        institution = getattr(request.user.profile, "institution", None)
        if not institution:
            return HttpResponse("No institution associated with your account", status=400)
        
        fee_structures_qs = FeeStructure.objects.filter(institution=institution)

        # Apply filters
        filters = Q()

        if class_id:
            filters &= Q(class_name_id=class_id)
            class_obj = get_object_or_404(Class, id=class_id, institution=institution)
        else:
            class_obj = None

        if academic_year_id:
            filters &= Q(academic_year_id=academic_year_id)
            academic_year_obj = get_object_or_404(AcademicYear, id=academic_year_id, institution=institution)
        else:
            academic_year_obj = None

        if is_active is not None:
            if is_active == "true":
                filters &= Q(is_active=True)
            elif is_active == "false":
                filters &= Q(is_active=False)

        fee_structures_qs = fee_structures_qs.filter(filters).order_by('class_name__name', 'academic_year__name')

        # Build filename
        filename_parts = ["fee_structures"]
        if class_obj:
            filename_parts.append(f"Class_{class_obj.name}")
        if academic_year_obj:
            filename_parts.append(f"Year_{academic_year_obj.name}")
        if is_active == "true":
            filename_parts.append("Active")
        elif is_active == "false":
            filename_parts.append("Inactive")

        filename = "_".join(filename_parts)

        # Build data rows
        rows = []
        for fee in fee_structures_qs:
            rows.append({
                "name": fee.name,
                "class_name": str(fee.class_name),
                "academic_year": str(fee.academic_year),
                "amount": f"{fee.amount:.2f}",
                "is_active": "Yes" if fee.is_active else "No",
                "created_at": fee.created_at.strftime("%Y-%m-%d"),
                "updated_at": fee.updated_at.strftime("%Y-%m-%d"),
            })

        # Handle empty results
        if not rows:
            if fmt == "pdf":
                context = {
                    "fee_structures": [],
                    "generated_date": timezone.now(),
                    "class_obj": class_obj,
                    "academic_year_obj": academic_year_obj,
                    "is_active_filter": is_active,
                    "no_data": True,
                    "organization": institution,
                }
                pdf_bytes = render_to_pdf("finance/export/fee_structures_pdf.html", context)
                if pdf_bytes:
                    return export_pdf_response(pdf_bytes, f"{filename}.pdf")
                return HttpResponse("Error generating PDF", status=500)
            else:
                return HttpResponse("No data found for the selected filters", status=404)

        # CSV Export
        if fmt == "csv":
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["Name", "Class", "Academic Year", "Amount", "Active", "Created At", "Updated At"])
            for r in rows:
                writer.writerow([
                    r["name"], r["class_name"], r["academic_year"],
                    r["amount"], r["is_active"], r["created_at"], r["updated_at"]
                ])
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            return resp

        # PDF Export
        elif fmt == "pdf":
            context = {
                "fee_structures": rows,
                "generated_date": timezone.now(),
                "class_obj": class_obj,
                "academic_year_obj": academic_year_obj,
                "is_active_filter": is_active,
                "organization": institution,
                "logo": getattr(institution.logo, 'url', None) if institution else None,
                "stamp": getattr(institution.stamp, 'url', None) if institution else None,
            }
            pdf_bytes = render_to_pdf("finance/export/fee_structures_pdf.html", context)
            if pdf_bytes:
                return export_pdf_response(pdf_bytes, f"{filename}.pdf")
            return HttpResponse("Error generating PDF", status=500)

        # Excel Export (placeholder - you might need to implement this with a library like openpyxl)
        elif fmt == "excel":
            # For Excel export, you might want to use a library like openpyxl or pandas
            # For now, we'll return CSV with Excel content type
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["Name", "Class", "Academic Year", "Amount", "Active", "Created At", "Updated At"])
            for r in rows:
                writer.writerow([
                    r["name"], r["class_name"], r["academic_year"],
                    r["amount"], r["is_active"], r["created_at"], r["updated_at"]
                ])
            resp = HttpResponse(buffer.getvalue(), content_type="application/vnd.ms-excel")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.xls"'
            return resp

        return HttpResponse("Invalid export format", status=400)