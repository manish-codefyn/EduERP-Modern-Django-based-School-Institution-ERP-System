from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import  PermissionRequiredMixin
from apps.core.mixins import LibraryManagerRequiredMixin
from apps.core.utils import get_user_institution
from .models import Author
from .forms import AuthorForm

class AuthorListView(LibraryManagerRequiredMixin, ListView):
    model = Author
    template_name = 'library/authors/author_list.html'
    context_object_name = 'authors'
    paginate_by = 20
    permission_required = 'library.view_author'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Author.objects.filter(institution=institution).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        context['total_authors'] = Author.objects.filter(institution=institution).count()
        return context

class AuthorCreateView( LibraryManagerRequiredMixin,PermissionRequiredMixin, CreateView):
    model = Author
    form_class = AuthorForm
    template_name = 'library/authors/author_form.html'
    permission_required = 'library.add_author'

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, "Author created successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('library:author_detail', kwargs={'pk': self.object.pk})

class AuthorUpdateView(LibraryManagerRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Author
    form_class = AuthorForm
    template_name = 'library/authors/author_form.html'
    permission_required = 'library.change_author'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Author.objects.filter(institution=institution)

    def form_valid(self, form):
        messages.success(self.request, "Author updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('library:author_detail', kwargs={'pk': self.object.pk})

class AuthorDetailView( LibraryManagerRequiredMixin,PermissionRequiredMixin, DetailView):
    model = Author
    template_name = 'library/authors/author_detail.html'
    context_object_name = 'author'
    permission_required = 'library.view_author'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Author.objects.filter(institution=institution)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['books'] = self.object.books.all()
        return context

class AuthorDeleteView( LibraryManagerRequiredMixin,PermissionRequiredMixin, DeleteView):
    model = Author
    template_name = 'library/authors/author_confirm_delete.html'
    context_object_name = 'author'
    success_url = reverse_lazy('library:author_list')
    permission_required = 'library.delete_author'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Author.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        author_name = self.object.name
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Author "{author_name}" has been deleted successfully.')
        return response