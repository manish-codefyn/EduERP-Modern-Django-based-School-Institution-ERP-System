from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import  PermissionRequiredMixin
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import HttpResponse
from io import BytesIO
import csv
import xlsxwriter
from datetime import datetime

from .models import Book, Author, BorrowRecord, Reservation, Category
from .forms import BookForm, AuthorForm, BorrowBookForm, ReturnBookForm, CategoryForm, ReservationForm
from apps.core.utils import get_user_institution
from apps.core.mixins import LibraryManagerRequiredMixin, StaffManagementRequiredMixin


class LibraryDashboardView( LibraryManagerRequiredMixin, ListView):
    template_name = 'library/dashboard.html'
    context_object_name = 'recent_books'

    def get_queryset(self):
        institution_id = get_user_institution(self.request.user).id
        queryset = Book.objects.filter(institution_id=institution_id).order_by('-created_at')[:10]
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution_id = get_user_institution(self.request.user).id
        
        context['total_books'] = Book.objects.filter(institution_id=institution_id).count()
        context['total_authors'] = Author.objects.count()
        context['active_borrows'] = BorrowRecord.objects.filter(
            institution_id=institution_id, 
            status='active'
        ).count()
        context['overdue_books'] = BorrowRecord.objects.filter(
            institution_id=institution_id,
            status='active', 
            due_date__lt=timezone.now()
        ).count()
        return context


# Author Views
class AuthorListView(LibraryManagerRequiredMixin, ListView):
    model = Author
    template_name = 'library/author/author_list.html'
    context_object_name = 'authors'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(bio__icontains=search_query)
            )
        return queryset


class AuthorDetailView(LibraryManagerRequiredMixin, DetailView):
    model = Author
    template_name = 'library/author/author_detail.html'
    context_object_name = 'author'


class AuthorCreateView(LibraryManagerRequiredMixin,PermissionRequiredMixin, CreateView):
    model = Author
    form_class = AuthorForm
    template_name = 'library/author/author_form.html'
    permission_required = 'library.add_author'

    def get_success_url(self):
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            return reverse_lazy('library:author_list', kwargs={'institution_id': institution_id})
        return reverse_lazy('library:author_list')


class AuthorUpdateView(LibraryManagerRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Author
    form_class = AuthorForm
    template_name = 'library/author/author_form.html'
    permission_required = 'library.change_author'

    # Use pk (UUID) instead of slug
    # No need for slug_field or slug_url_kwarg

    def get_success_url(self):
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            return reverse_lazy('library:author_detail', kwargs={
                'institution_id': institution_id,
                'pk': self.object.pk  # use UUID pk here
            })
        return reverse_lazy('library:author_detail', kwargs={'pk': self.object.pk})



class AuthorDeleteView( LibraryManagerRequiredMixin,PermissionRequiredMixin, DeleteView):
    model = Author
    template_name = 'library/author/author_confirm_delete.html'
    permission_required = 'library.delete_author'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_success_url(self):
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            return reverse_lazy('library:author-list', kwargs={'institution_id': institution_id})
        return reverse_lazy('library:author-list')


# Category Views
class CategoryListView( LibraryManagerRequiredMixin, ListView):
    model = Category
    template_name = 'library/category/category_list.html'
    context_object_name = 'categories'
    paginate_by = 20


class CategoryDetailView( LibraryManagerRequiredMixin,DetailView):
    model = Category
    template_name = 'library/category/category_detail.html'
    context_object_name = 'category'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['books'] = self.object.book_set.all().select_related('author')
        return context


class CategoryCreateView(LibraryManagerRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'library/category/category_form.html'
    permission_required = 'library.add_category'

    def get_success_url(self):
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            return reverse_lazy('library:category-list', kwargs={'institution_id': institution_id})
        return reverse_lazy('library:category-list')


class CategoryUpdateView(LibraryManagerRequiredMixin,PermissionRequiredMixin,  UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'library/category/category_form.html'
    permission_required = 'library.change_category'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_success_url(self):
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            return reverse_lazy('library:category-detail', kwargs={
                'institution_id': institution_id,
                'slug': self.object.slug
            })
        return reverse_lazy('library:category-detail', kwargs={'slug': self.object.slug})


class CategoryDeleteView( LibraryManagerRequiredMixin,PermissionRequiredMixin,  DeleteView):
    model = Category
    template_name = 'library/category/category_confirm_delete.html'
    permission_required = 'library.delete_category'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_success_url(self):
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            return reverse_lazy('library:category-list', kwargs={'institution_id': institution_id})
        return reverse_lazy('library:category-list')


# Borrow Record Views
class BorrowRecordListView( LibraryManagerRequiredMixin, ListView):
    model = BorrowRecord
    template_name = 'library/borrow/borrowrecord_list.html'
    context_object_name = 'borrow_records'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.GET.get('status')
        user_filter = self.request.GET.get('user')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if user_filter:
            queryset = queryset.filter(borrower__username__icontains=user_filter)
        
        return queryset.select_related('book', 'borrower')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['overdue_records'] = BorrowRecord.objects.filter(
            institution_id=self.kwargs.get('institution_id'),
            status='active',
            due_date__lt=timezone.now()
        )
        return context


class BorrowRecordDetailView( LibraryManagerRequiredMixin,DetailView):
    model = BorrowRecord
    template_name = 'library/borrow/borrowrecord_detail.html'
    context_object_name = 'borrow_record'


class BorrowBookView( LibraryManagerRequiredMixin,PermissionRequiredMixin,  CreateView):
    model = BorrowRecord
    form_class = BorrowBookForm
    template_name = 'library/borrow/borrow_book_form.html'
    permission_required = 'library.add_borrowrecord'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            kwargs['institution_id'] = institution_id
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        # Update book available copies
        book = form.instance.book
        if book.available_copies > 0:
            book.available_copies -= 1
            if book.available_copies == 0:
                book.status = 'borrowed'
            book.save()
        messages.success(self.request, f'Book "{book.title}" has been borrowed successfully.')
        return response

    def get_success_url(self):
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            return reverse_lazy('library:borrowrecord-list', kwargs={'institution_id': institution_id})
        return reverse_lazy('library:borrowrecord-list')


class ReturnBookView( LibraryManagerRequiredMixin,PermissionRequiredMixin, UpdateView):
    model = BorrowRecord
    form_class = ReturnBookForm
    template_name = 'library/borrow/return_book_form.html'
    permission_required = 'library.change_borrowrecord'

    def form_valid(self, form):
        form.instance.returned_date = timezone.now()
        form.instance.status = 'returned'
        response = super().form_valid(form)
        
        # Update book available copies
        book = form.instance.book
        book.available_copies += 1
        if book.status == 'borrowed':
            book.status = 'available'
        book.save()
        
        messages.success(self.request, f'Book "{book.title}" has been returned successfully.')
        return response

    def get_success_url(self):
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            return reverse_lazy('library:borrowrecord-list', kwargs={'institution_id': institution_id})
        return reverse_lazy('library:borrowrecord-list')


# Reservation Views
class ReservationListView( LibraryManagerRequiredMixin, ListView):
    model = Reservation
    template_name = 'library/reservation/reservation_list.html'
    context_object_name = 'reservations'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.GET.get('status')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.select_related('book', 'user')


class ReservationCreateView(LibraryManagerRequiredMixin, CreateView):
    model = Reservation
    form_class = ReservationForm
    template_name = 'library/reservation/reservation_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            kwargs['institution_id'] = institution_id
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Book has been reserved successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            return reverse_lazy('library:reservation-list', kwargs={'institution_id': institution_id})
        return reverse_lazy('library:reservation-list')


class ReservationUpdateView( LibraryManagerRequiredMixin,PermissionRequiredMixin, UpdateView):
    model = Reservation
    form_class = ReservationForm
    template_name = 'library/reservation/reservation_form.html'
    permission_required = 'library.change_reservation'

    def get_success_url(self):
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            return reverse_lazy('library:reservation-list', kwargs={'institution_id': institution_id})
        return reverse_lazy('library:reservation-list')


class ReservationDeleteView(LibraryManagerRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Reservation
    template_name = 'library/reservation/reservation_confirm_delete.html'
    permission_required = 'library.delete_reservation'

    def get_success_url(self):
        institution_id = self.kwargs.get('institution_id')
        if institution_id:
            return reverse_lazy('library:reservation-list', kwargs={'institution_id': institution_id})
        return reverse_lazy('library:reservation-list')


# Search View
class LibrarySearchView(LibraryManagerRequiredMixin, ListView):
    model = Book
    template_name = 'library/search_results.html'
    context_object_name = 'books'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(author__name__icontains=query) |
                Q(isbn__icontains=query) |
                Q(publisher__icontains=query) |
                Q(description__icontains=query)
            )
        
        return queryset.select_related('author', 'category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context

