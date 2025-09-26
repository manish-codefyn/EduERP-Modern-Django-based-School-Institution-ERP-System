import csv
from io import StringIO, BytesIO
from datetime import datetime
import xlsxwriter
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from apps.core.utils import get_user_institution
from .models import Book, Author, Category

# Export Views
class BookExportView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Book
    context_object_name = "books"
    permission_required = 'library.view_book'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Book.objects.select_related('author', 'category').filter(institution=institution)

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "csv").lower()
        queryset = self.get_queryset()

        filename = f"books_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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

        writer.writerow(['Title', 'Author', 'ISBN', 'Category', 'Publisher', 'Publication Date', 
                        'Edition', 'Quantity', 'Available Copies', 'Status', 'Location'])

        for book in queryset:
            writer.writerow([
                book.title,
                book.author.name if book.author else '',
                book.isbn or '',
                book.category.name if book.category else '',
                book.publisher or '',
                book.publication_date.strftime('%Y-%m-%d') if book.publication_date else '',
                book.edition or '',
                book.quantity,
                book.available_copies,
                book.get_status_display(),
                book.location or ''
            ])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, queryset, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Books")

            header_format = workbook.add_format({
                "bold": True, "bg_color": "#2c3e50", "font_color": "white",
                "border": 1, "align": "center", "valign": "vcenter"
            })

            headers = ['Title', 'Author', 'ISBN', 'Category', 'Publisher', 'Publication Date', 
                      'Edition', 'Quantity', 'Available Copies', 'Status', 'Location']
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, book in enumerate(queryset, start=1):
                worksheet.write(row_idx, 0, book.title)
                worksheet.write(row_idx, 1, book.author.name if book.author else '')
                worksheet.write(row_idx, 2, book.isbn or '')
                worksheet.write(row_idx, 3, book.category.name if book.category else '')
                worksheet.write(row_idx, 4, book.publisher or '')
                worksheet.write(row_idx, 5, book.publication_date.strftime('%Y-%m-%d') if book.publication_date else '')
                worksheet.write(row_idx, 6, book.edition or '')
                worksheet.write(row_idx, 7, book.quantity)
                worksheet.write(row_idx, 8, book.available_copies)
                worksheet.write(row_idx, 9, book.get_status_display())
                worksheet.write(row_idx, 10, book.location or '')

            worksheet.set_column('A:A', 30)  # Title
            worksheet.set_column('B:B', 25)  # Author
            worksheet.set_column('C:C', 15)  # ISBN
            worksheet.set_column('D:D', 20)  # Category
            worksheet.set_column('E:E', 20)  # Publisher
            worksheet.set_column('F:F', 15)  # Publication Date
            worksheet.set_column('G:G', 10)  # Edition
            worksheet.set_column('H:I', 12)  # Quantity, Available Copies
            worksheet.set_column('J:J', 15)  # Status
            worksheet.set_column('K:K', 20)  # Location

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
            "books": queryset,
            "total_count": queryset.count(),
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Books Export",
        }
        pdf_bytes = render_to_pdf("library/export/books_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)


class AuthorExportView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Author
    context_object_name = "authors"
    permission_required = 'library.view_author'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Author.objects.filter(institution=institution)

    def get(self, request, *args, **kwargs):
        # Similar export implementation for authors
        pass

class CategoryExportView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Category
    context_object_name = "categories"
    permission_required = 'library.view_category'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Category.objects.filter(institution=institution)

    def get(self, request, *args, **kwargs):
        # Similar export implementation for categories
        pass