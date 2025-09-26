from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import PermissionRequiredMixin
from apps.core.mixins import LibraryManagerRequiredMixin
from apps.core.utils import get_user_institution
from .models import Category
from .forms import CategoryForm


class CategoryListView(LibraryManagerRequiredMixin, ListView):
    model = Category
    template_name = 'library/categories/category_list.html'
    context_object_name = 'categories'
    paginate_by = 20
    permission_required = 'library.view_category'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Category.objects.filter(institution=institution).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        context['total_categories'] = Category.objects.filter(institution=institution).count()
        return context

class CategoryCreateView(LibraryManagerRequiredMixin,PermissionRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'library/categories/category_form.html'
    permission_required = 'library.add_category'

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, "Category created successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('library:category_detail', kwargs={'pk': self.object.pk})

class CategoryUpdateView(LibraryManagerRequiredMixin,PermissionRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'library/categories/category_form.html'
    permission_required = 'library.change_category'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Category.objects.filter(institution=institution)

    def form_valid(self, form):
        messages.success(self.request, "Category updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('library:category_detail', kwargs={'pk': self.object.pk})

class CategoryDetailView(LibraryManagerRequiredMixin,PermissionRequiredMixin, DetailView):
    model = Category
    template_name = 'library/categories/category_detail.html'
    context_object_name = 'category'
    permission_required = 'library.view_category'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Category.objects.filter(institution=institution)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['books'] = self.object.books.all()
        return context

class CategoryDeleteView(LibraryManagerRequiredMixin,PermissionRequiredMixin, DeleteView):
    model = Category
    template_name = 'library/categories/category_confirm_delete.html'
    context_object_name = 'category'
    success_url = reverse_lazy('library:category_list')
    permission_required = 'library.delete_category'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Category.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        category_name = self.object.name
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Category "{category_name}" has been deleted successfully.')
        return response