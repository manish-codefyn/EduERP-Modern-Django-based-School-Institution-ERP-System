from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import  PermissionRequiredMixin
from apps.core.mixins import LibraryManagerRequiredMixin
from apps.core.utils import get_user_institution
from .models import BorrowRecord
from .forms import BorrowBookForm,ReturnBookForm

# -------------------------------------------------------------------
# Borrow Record Views
# -------------------------------------------------------------------
class BorrowRecordListView(LibraryManagerRequiredMixin, ListView):
    model = BorrowRecord
    template_name = 'library/borrow/borrowrecord_list.html'
    context_object_name = 'borrows'
    paginate_by = 20
    permission_required = 'library.view_borrowrecord'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        qs = BorrowRecord.objects.filter(institution=institution).select_related('book', 'borrower')
        status_filter = self.request.GET.get('status')
        user_filter = self.request.GET.get('user')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if user_filter:
            qs = qs.filter(borrower__username__icontains=user_filter)
        return qs.order_by('-borrowed_date')


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        context['overdue_records'] = BorrowRecord.objects.filter(institution=institution, status='active', due_date__lt=timezone.now())
        return context


class BorrowRecordDetailView(LibraryManagerRequiredMixin, DetailView):
    model = BorrowRecord
    template_name = 'library/borrow/borrowrecord_detail.html'
    context_object_name = 'borrow_record'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return BorrowRecord.objects.filter(institution=institution)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.now()
        return context

class BorrowBookView(LibraryManagerRequiredMixin, PermissionRequiredMixin,CreateView):
    model = BorrowRecord
    form_class = BorrowBookForm
    template_name = 'library/borrow/borrow_book_form.html'
    permission_required = 'library.add_borrowrecord'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['institution_id'] = get_user_institution(self.request.user).id
        return kwargs

    def form_valid(self, form):
        # set institution & user
        form.instance.institution = get_user_institution(self.request.user)
        response = super().form_valid(form)

        # Update book copies
        book = form.instance.book
        if book and book.available_copies > 0:
            book.available_copies -= 1
            if book.available_copies == 0:
                book.status = 'borrowed'
            book.save()

        messages.success(self.request, f'Book "{book.title}" has been borrowed successfully.')
        return response

    def get_success_url(self):
        return reverse('library:borrowrecord_list')


class ReturnBookView(LibraryManagerRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = BorrowRecord
    form_class = ReturnBookForm
    template_name = 'library/borrow/return_book_form.html'
    permission_required = 'library.change_borrowrecord'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return BorrowRecord.objects.filter(institution=institution)

    def form_valid(self, form):
        # Set return date and status
        form.instance.return_date = timezone.now()
        form.instance.status = 'returned'
        response = super().form_valid(form)

        # Update book availability
        book = form.instance.book
        if book:
            book.available_copies = (book.available_copies or 0) + 1
            if book.status == 'borrowed':
                book.status = 'available'
            book.save()

        messages.success(self.request, f'Book "{book.title}" has been returned successfully.')
        return response

    def get_success_url(self):
        return reverse('library:borrowrecord_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        borrow_record = self.object
        context['today'] = timezone.now()
        context['borrow_record_url'] = reverse('library:borrowrecord_detail', kwargs={'pk': borrow_record.id})

        # Fine calculation
        fine_rate_per_day = 0.5  # Default fine rate, you can make it dynamic
        overdue_days = 0
        calculated_fine = 0.0
        if borrow_record.due_date and borrow_record.due_date < context['today']:
            delta = context['today'] - borrow_record.due_date
            overdue_days = delta.days
            calculated_fine = overdue_days * fine_rate_per_day

        context['fine_rate_per_day'] = fine_rate_per_day
        context['overdue_days'] = overdue_days
        context['calculated_fine'] = f"{calculated_fine:.2f}"

        return context
