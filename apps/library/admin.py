from django.contrib import admin
from .models import Author, Category, Book, BorrowRecord, Reservation

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['name', 'date_of_birth', 'date_of_death']
    search_fields = ['name']
    list_filter = ['created_at']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'institution']
    search_fields = ['name', 'institution__name']
    list_filter = ['institution']

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'institution', 'category', 'quantity', 'available_copies', 'status']
    list_filter = ['institution', 'category', 'status', 'created_at']
    search_fields = ['title', 'author__name', 'isbn', 'institution__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(BorrowRecord)
class BorrowRecordAdmin(admin.ModelAdmin):
    list_display = ['book', 'borrower', 'institution', 'borrowed_date', 'due_date', 'status']
    list_filter = ['institution', 'status', 'borrowed_date']
    search_fields = ['book__title', 'borrower__username', 'institution__name']


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        'reservation_number', 'book', 'user', 'institution', 
        'reservation_date', 'expiry_date', 'status'
    )
    list_filter = ('status', 'institution', 'reservation_date')
    search_fields = ('reservation_number', 'book__title', 'user__username', 'user__email')
    
    readonly_fields = ('reservation_number', 'reservation_date')  # Show reservation number but not editable

    fieldsets = (
        (None, {
            'fields': ('reservation_number', 'institution', 'book', 'user', 'status', 'notes')
        }),
        ('Dates', {
            'fields': ('reservation_date', 'expiry_date')
        }),
    )
