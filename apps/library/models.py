import uuid
import random
import string
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

# Get the User model
User = get_user_model()


class Author(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    name = models.CharField(max_length=200)
    bio = models.TextField(blank=True, null=True)
    institution = models.ForeignKey(
        "organization.Institution",
        on_delete=models.CASCADE,
        related_name="library_authors",
        verbose_name=_("Institution")
    )
    date_of_birth = models.DateField(blank=True, null=True)
    date_of_death = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['institution', 'name']

    def __str__(self):
        return f"{self.name} ({self.institution.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure slug is unique
            original_slug = self.slug
            counter = 1
            while Author.objects.filter(institution=self.institution, slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('library:author_detail', kwargs={'pk': self.id})

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, blank=True)
    institution = models.ForeignKey(
        "organization.Institution", 
        on_delete=models.CASCADE, 
        related_name="library_categories",
        verbose_name=_("Institution")
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
        unique_together = ['institution', 'name']

    def __str__(self):
        return f"{self.name} ({self.institution.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure slug is unique within institution
            original_slug = self.slug
            counter = 1
            while Category.objects.filter(institution=self.institution, slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('library:category-detail', kwargs={'slug': self.slug})
    
    @property
    def total_books(self):
        """
        Returns the total number of books in this category.
        """
        return self.books.count()

class Book(models.Model):
    BOOK_STATUS = [
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('reserved', 'Reserved'),
        ('lost', 'Lost'),
        ('maintenance', 'Under Maintenance'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=200, blank=True)
    institution = models.ForeignKey(
        "organization.Institution", 
        on_delete=models.CASCADE, 
        related_name="library_books",
        verbose_name=_("Institution")
    )
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    isbn = models.CharField('ISBN', max_length=13, unique=True, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True,related_name='books')
    publisher = models.CharField(max_length=200, blank=True, null=True)
    publication_date = models.DateField(blank=True, null=True)
    edition = models.CharField(max_length=50, blank=True, null=True)
    pages = models.IntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    quantity = models.IntegerField(default=1)
    available_copies = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=BOOK_STATUS, default='available')
    location = models.CharField(max_length=100, blank=True, null=True)
    cover_image = models.ImageField(upload_to='book_covers/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        unique_together = ['institution', 'isbn']

    def __str__(self):
        return f"{self.title} - {self.institution.name}"

    def save(self, *args, **kwargs):
        # Generate slug
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure slug is unique within institution
            original_slug = self.slug
            counter = 1
            while Book.objects.filter(institution=self.institution, slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        # Set available copies if not set
        if not self.available_copies:
            self.available_copies = self.quantity
            
        super().save(*args, **kwargs)


    def get_absolute_url(self):
        return reverse('library:book_detail', kwargs={'pk': self.id})


class BorrowRecord(models.Model):
    BORROW_STATUS = [
        ('active', 'Active'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('lost', 'Lost'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        "organization.Institution", 
        on_delete=models.CASCADE, 
        related_name="library_borrows",
        verbose_name=_("Institution")
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrow_records')
    borrower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowed_books')
    borrowed_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField()
    returned_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=BORROW_STATUS, default='active')
    fine_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_borrows')

    class Meta:
        ordering = ['-borrowed_date']

    def __str__(self):
        return f"{self.book.title} - {self.borrower.username} - {self.institution.name}"

    def is_overdue(self):
        return timezone.now() > self.due_date and self.status == 'active'

    def calculate_fine(self):
        if self.is_overdue() and self.status == 'active':
            days_overdue = (timezone.now() - self.due_date).days
            return days_overdue * 5  # $5 per day fine
        return 0

    def get_absolute_url(self):
        return reverse('library:borrow-detail', kwargs={'pk': self.id})


class Reservation(models.Model):
    RESERVATION_STATUS = [
        ('pending', 'Pending'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation_number = models.CharField(
        max_length=12, unique=True, editable=False, verbose_name="Reservation Number"
    )
    institution = models.ForeignKey(
        "organization.Institution", 
        on_delete=models.CASCADE, 
        related_name="library_reservations",
        verbose_name=_("Institution")
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reservations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    reservation_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=RESERVATION_STATUS, default='pending')
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-reservation_date']

    def __str__(self):
        return f"{self.book.title} - {self.user.username} - {self.institution.name}"

    def get_absolute_url(self):
        return reverse('library:reservation-detail', kwargs={'pk': self.id})
    
    @staticmethod
    def generate_unique_reservation_number(length=8):
        """Generate a unique alphanumeric reservation number"""
        while True:
            number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            if not Reservation.objects.filter(reservation_number=number).exists():
                return number
            

    def save(self, *args, **kwargs):
        if not self.reservation_number:
            self.reservation_number = self.generate_unique_reservation_number()
        super().save(*args, **kwargs)