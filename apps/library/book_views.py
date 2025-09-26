import csv
from io import StringIO, BytesIO
from datetime import datetime, timedelta, date
import xlsxwriter
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Count, Q, Sum, Case, When, IntegerField
from django.db import models
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from apps.core.mixins import LibraryManagerRequiredMixin
from apps.core.utils import get_user_institution
from .models import Book, Author, Category
from .forms import BookForm, BookFilterForm

# Dashboard View
class BookDashboardView(LibraryManagerRequiredMixin, TemplateView):
    template_name = 'library/books/dashboard.html'
    permission_required = 'library.view_book'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Basic statistics
        total_books = Book.objects.filter(institution=institution).count()
        total_authors = Author.objects.filter(book__institution=institution).distinct().count()
        total_categories = Category.objects.filter(book__institution=institution).distinct().count()
        
        # Book status breakdown
        book_status = Book.objects.filter(institution=institution).aggregate(
            total_copies=Sum('quantity'),
            available_copies=Sum('available_copies'),
            available_books=Count('id', filter=Q(status='available')),
            borrowed_books=Count('id', filter=Q(status='borrowed')),
            reserved_books=Count('id', filter=Q(status='reserved')),
            maintenance_books=Count('id', filter=Q(status='maintenance')),
            lost_books=Count('id', filter=Q(status='lost'))
        )
        
        # Recent books added
        recent_books = Book.objects.filter(
            institution=institution
        ).select_related('author', 'category').order_by('-created_at')[:10]
        
        # Popular books (most copies)
        popular_books = Book.objects.filter(
            institution=institution
        ).select_related('author').order_by('-quantity')[:5]
        
        # Low quantity books
        low_quantity_books = Book.objects.filter(
            institution=institution,
            quantity__lte=5  # Less than 5 copies
        ).order_by('quantity')[:5]
        
        # Monthly addition chart data
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_data = Book.objects.filter(
            institution=institution,
            created_at__gte=six_months_ago
        ).extra({
            'month': "EXTRACT(month FROM created_at)",
            'year': "EXTRACT(year FROM created_at)"
        }).values('year', 'month').annotate(
            books_added=Count('id')
        ).order_by('year', 'month')
        
        context.update({
            'total_books': total_books,
            'total_authors': total_authors,
            'total_categories': total_categories,
            'total_copies': book_status['total_copies'] or 0,
            'available_copies': book_status['available_copies'] or 0,
            'available_books': book_status['available_books'] or 0,
            'borrowed_books': book_status['borrowed_books'] or 0,
            'reserved_books': book_status['reserved_books'] or 0,
            'maintenance_books': book_status['maintenance_books'] or 0,
            'lost_books': book_status['lost_books'] or 0,
            'recent_books': recent_books,
            'popular_books': popular_books,
            'low_quantity_books': low_quantity_books,
            'monthly_data': list(monthly_data),
        })
        return context

    def has_permission(self):
        return self.request.user.has_perm('library.view_book')


# Book List View
class BookListView(LibraryManagerRequiredMixin, ListView):
    model = Book
    template_name = 'library/books/book_list.html'
    context_object_name = 'books'
    paginate_by = 20
    permission_required = 'library.view_book'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = Book.objects.filter(institution=institution).select_related('author', 'category', 'institution')

        # Apply filters
        form = BookFilterForm(self.request.GET, institution=institution)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            author = form.cleaned_data.get('author')
            category = form.cleaned_data.get('category')
            status = form.cleaned_data.get('status')
            isbn = form.cleaned_data.get('isbn')

            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) | 
                    Q(publisher__icontains=search) |
                    Q(description__icontains=search)
                )
            if author:
                queryset = queryset.filter(author=author)
            if category:
                queryset = queryset.filter(category=category)
            if status:
                queryset = queryset.filter(status=status)
            if isbn:
                queryset = queryset.filter(isbn__icontains=isbn)

        return queryset.order_by('title')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Statistics
        stats = Book.objects.filter(institution=institution).aggregate(
            total_books=Count('id'),
            total_copies=Sum('quantity'),
            available_copies=Sum('available_copies')
        )
        
        context['filter_form'] = BookFilterForm(self.request.GET, institution=institution)
        context.update(stats)
        return context

    def has_permission(self):
        return self.request.user.has_perm('library.view_book')


class BookCreateView(LibraryManagerRequiredMixin,PermissionRequiredMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = 'library/books/book_form.html'
    permission_required = 'library.add_book'

    def form_valid(self, form):
        # Automatically set institution from the logged-in user
        form.instance.institution = get_user_institution(self.request.user)
        
        # Set created_by to current user
        form.instance.created_by = self.request.user
        
        messages.success(self.request, "Book created successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add New Book"
        return context

    def get_success_url(self):
        return reverse('library:book_detail', kwargs={'pk': self.object.pk})


# Book Update View
class BookUpdateView(LibraryManagerRequiredMixin,PermissionRequiredMixin, UpdateView):
    model = Book
    form_class = BookForm
    template_name = 'library/books/book_form.html'
    permission_required = 'library.change_book'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Book.objects.filter(institution=institution)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['institution_id'] = self.object.institution_id
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Book updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('library:book_detail', kwargs={'pk': self.object.pk})

# Book Detail View
class BookDetailView(LibraryManagerRequiredMixin,PermissionRequiredMixin, DetailView):
    model = Book
    template_name = 'library/books/book_detail.html'
    context_object_name = 'book'
    
    # Allow both view and change permissions
    permission_required = ('library.view_book', 'library.change_book')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Book.objects.filter(institution=institution)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add related data like borrowing history, etc.
        # context['borrow_history'] = BorrowRecord.objects.filter(book=self.object).order_by('-borrow_date')[:10]
        return context


# Book Delete View
class BookDeleteView(LibraryManagerRequiredMixin,PermissionRequiredMixin, DeleteView):
    model = Book
    template_name = 'library/books/book_confirm_delete.html'
    context_object_name = 'book'
    success_url = reverse_lazy('library:book_list')
    permission_required = 'library.delete_book'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Book.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        book_title = self.object.title
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Book "{book_title}" has been deleted successfully.')
        return response




# API Views
@require_GET
def get_book_details(request, pk):
    """API endpoint to get book details"""
    institution = get_user_institution(request.user)
    book = get_object_or_404(Book, pk=pk, institution=institution)
    
    return JsonResponse({
        'title': book.title,
        'author': book.author.name if book.author else '',
        'isbn': book.isbn or '',
        'quantity': book.quantity,
        'available_copies': book.available_copies,
        'status': book.status,
        'location': book.location or ''
    })


@require_GET
def check_isbn_availability(request):
    """Check if ISBN is available within the institution"""
    institution = get_user_institution(request.user)
    isbn = request.GET.get('isbn')
    book_id = request.GET.get('book_id')  # For update operations
    
    if not isbn:
        return JsonResponse({'available': True})
    
    queryset = Book.objects.filter(institution=institution, isbn=isbn)
    if book_id:
        queryset = queryset.exclude(id=book_id)
    
    exists = queryset.exists()
    return JsonResponse({'available': not exists})


# Bulk Operations
class BookBulkUploadView(LibraryManagerRequiredMixin,PermissionRequiredMixin, TemplateView):
    template_name = 'library/books/bulk_upload.html'
    permission_required = 'library.add_book'

    def post(self, request, *args, **kwargs):
        institution = get_user_institution(request.user)
        # Handle CSV file upload and bulk creation
        # Implementation depends on your specific requirements
        pass