from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Book, Author, BorrowRecord, Reservation, Category
from django.utils import timezone
from apps.core.utils import get_user_institution
from django.contrib.auth import get_user_model

User = get_user_model()


class BookFilterForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': _('Search by title, publisher, description...'),
        'class': 'form-control'
    }))
    
    author = forms.ModelChoiceField(
        queryset=Author.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Book.BOOK_STATUS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    isbn = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': _('Search by ISBN...'),
            'class': 'form-control'
        })
    )

    def __init__(self, *args, **kwargs):
        institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        if institution:
            self.fields['author'].queryset = Author.objects.filter(
                institution=institution
            ).distinct()
            self.fields['category'].queryset = Category.objects.filter(
                institution=institution
            ).distinct()


class BookForm(forms.ModelForm):
    publication_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text=_("Format: YYYY-MM-DD")
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        help_text=_("Total number of copies")
    )

    class Meta:
        model = Book
        fields = [
            'title', 'author', 'isbn', 'category', 'publisher', 
            'publication_date', 'edition', 'pages', 'description',
            'quantity', 'location', 'cover_image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Book title')}),
            'author': forms.Select(attrs={'class': 'form-control'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('13-digit ISBN')}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Publisher name')}),
            'edition': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Edition information')}),
            'pages': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': _('Book description')}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Shelf location')}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
        help_texts = {
            'isbn': _('Optional 13-digit International Standard Book Number'),
        }

    def __init__(self, *args, **kwargs):
        self.institution_id = kwargs.pop('institution_id', None)
        super().__init__(*args, **kwargs)
        
        # Set querysets based on institution
        if self.institution_id:
            self.fields['author'].queryset = Author.objects.filter(
                institution_id=self.institution_id
            ).distinct()
            self.fields['category'].queryset = Category.objects.filter(
                institution_id=self.institution_id
            ).distinct()
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

    def clean_isbn(self):
        isbn = self.cleaned_data.get('isbn')
        if isbn:
            # Basic ISBN validation
            isbn = isbn.replace('-', '').replace(' ', '')
            if not isbn.isdigit() or len(isbn) not in [10, 13]:
                raise forms.ValidationError(_("ISBN must be 10 or 13 digits."))
            
            # Check for unique ISBN within institution
            if self.institution_id:
                queryset = Book.objects.filter(institution_id=self.institution_id, isbn=isbn)
                if self.instance and self.instance.pk:
                    queryset = queryset.exclude(pk=self.instance.pk)
                if queryset.exists():
                    raise forms.ValidationError(_("A book with this ISBN already exists in this institution."))
        
        return isbn

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity and quantity < 1:
            raise forms.ValidationError(_("Quantity must be at least 1."))
        return quantity

    def clean_pages(self):
        pages = self.cleaned_data.get('pages')
        if pages and pages < 1:
            raise forms.ValidationError(_("Number of pages must be positive."))
        return pages
    
class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ['name', 'bio', 'date_of_birth', 'date_of_death']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'date_of_death': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'institution', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
            'institution': forms.Select(attrs={
                'class': 'form-select',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a short description',
                'rows': 3
            }),
        }
        help_texts = {
            'description': 'Optional description for the category.'
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, "institution"):
            self.fields['institution'].initial = user.institution
            self.fields['institution'].widget.attrs['readonly'] = True
            self.fields['institution'].widget.attrs['disabled'] = True  

            # add hidden field to preserve submission
            self.fields['institution_hidden'] = forms.ModelChoiceField(
                queryset=self.fields['institution'].queryset,
                initial=user.institution,
                widget=forms.HiddenInput()
            )

    def clean(self):
        cleaned_data = super().clean()
        if 'institution_hidden' in self.fields:
            cleaned_data['institution'] = cleaned_data.get('institution_hidden')
        return cleaned_data

class BorrowBookForm(forms.ModelForm):
    class Meta:
        model = BorrowRecord
        fields = ['institution', 'book', 'borrower', 'due_date']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'institution': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        # Pop 'user' from kwargs if it exists
        self.user = kwargs.pop('user', None)
        self.institution_id = kwargs.pop('institution_id', None)
        super().__init__(*args, **kwargs)

        # If institution_id is passed, set it and disable the field
        if self.institution_id:
            self.fields['institution'].initial = self.institution_id
            self.fields['institution'].disabled = True

        # Optional: Limit books to only those available
        if self.institution_id:
            self.fields['book'].queryset = Book.objects.filter(
                institution_id=self.institution_id,
                available_copies__gt=0
            )


class ReturnBookForm(forms.ModelForm):
    class Meta:
        model = BorrowRecord
        fields = ['returned_date', 'fine_amount', 'notes']
        widgets = {
            'returned_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                    'value': timezone.now().strftime('%Y-%m-%dT%H:%M')
                }
            ),
            'fine_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'returned_date': 'Return Date',
            'fine_amount': 'Fine Amount',
            'notes': 'Return Notes',
        }

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['book', 'user', 'expiry_date', 'notes', 'status']
        widgets = {
            'expiry_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and self.request.user.is_authenticated:
            institution = get_user_institution(self.request.user)
            
            # Filter books and users by institution
            self.fields['book'].queryset = Book.objects.filter(institution=institution)
                    # Filter users by institution via UserProfile
            self.fields['user'].queryset = User.objects.filter(profile__institution=institution)

            
            # Set default expiry date (e.g., 7 days from now)
            if not self.instance.pk:  # Only for new reservations
                self.fields['expiry_date'].initial = timezone.now() + timezone.timedelta(days=7)

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date and expiry_date <= timezone.now():
            raise forms.ValidationError("Expiry date must be in the future.")
        return expiry_date

    def clean(self):
        cleaned_data = super().clean()
        book = cleaned_data.get('book')
        user = cleaned_data.get('user')
        
        if book and user:
            # Check if user already has a pending reservation for this book
            existing_reservation = Reservation.objects.filter(
                book=book,
                user=user,
                status='pending'
            ).exists()
            
            if existing_reservation and not self.instance.pk:
                raise forms.ValidationError(
                    "This user already has a pending reservation for this book."
                )
        
        return cleaned_data

class ReservationFilterForm(forms.Form):
    STATUS_CHOICES = [('', 'All Statuses')] + Reservation.RESERVATION_STATUS
    
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Search by book, user...'}))
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    
    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution')
        super().__init__(*args, **kwargs)