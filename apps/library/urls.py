from django.urls import path
from . import views
from . import author_views
from . import book_views
from . import export_views
from . import category_views
from . import borrow_views
from . import reservation
app_name = 'library'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.LibraryDashboardView.as_view(), name='dashboard'),
    
    # Author URLs
    path('authors/', author_views.AuthorListView.as_view(), name='author_list'),
    path('authors/add/', author_views.AuthorCreateView.as_view(), name='author_create'),
    path('authors/<uuid:pk>/', author_views.AuthorDetailView.as_view(), name='author_detail'),
    path('authors/<uuid:pk>/edit/', author_views.AuthorUpdateView.as_view(), name='author_update'),
    path('authors/<uuid:pk>/delete/', author_views.AuthorDeleteView.as_view(), name='author_delete'),
    # Book URLs
    path('books/', book_views.BookListView.as_view(), name='book_list'),
    path('books/add/',book_views.BookCreateView.as_view(), name='book_create'),
    path('books/<uuid:pk>/',book_views.BookDetailView.as_view(), name='book_detail'),
    path('books/<uuid:pk>/edit/',book_views.BookUpdateView.as_view(), name='book_update'),
    path('books/<uuid:pk>/delete/', book_views.BookDeleteView.as_view(), name='book_delete'),
    path('books/bulk-upload/', book_views.BookBulkUploadView.as_view(), name='book_bulk_upload'),

    # API Endpoints
    path('books/api/<uuid:pk>/', book_views.get_book_details, name='api_book_detail'),
    path('books/api/check-isbn/', book_views.check_isbn_availability, name='api_check_isbn'),
     # Book Export

    path('export/books/', export_views.BookExportView.as_view(), name='book_export'),
    # path('export/authors/', export_views.AuthorExportView.as_view(), name='export_authors'),
    # path('export/categories/', export_views.CategoryExportView.as_view(), name='export_categories'),
    # Bulk Upload


    # Category URLs
    path('categories/', category_views.CategoryListView.as_view(), name='category_list'),
    path('categories/<uuid:pk>/', category_views.CategoryDetailView.as_view(), name='category_detail'),
    path('categories/add/', category_views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<uuid:pk>/edit/', category_views.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<uuid:pk>/delete/', category_views.CategoryDeleteView.as_view(), name='category_delete'),
    
    # Borrow Record URLs
    path('borrow-records/', borrow_views.BorrowRecordListView.as_view(), name='borrowrecord_list'),
    path('borrow-records/<uuid:pk>/', borrow_views.BorrowRecordDetailView.as_view(), name='borrowrecord_detail'),
    path('borrow-records/borrow/', borrow_views.BorrowBookView.as_view(), name='borrow_book'),
    path('borrow-records/<uuid:pk>/return/', borrow_views.ReturnBookView.as_view(), name='return_book'),
    
    # Reservation URLs
     # Reservation URLs
    path('reservations/', reservation.ReservationListView.as_view(), name='reservation_list'),
    path('reservations/create/', reservation.ReservationCreateView.as_view(), name='reservation_create'),
    path('reservations/<uuid:pk>/', reservation.ReservationDetailView.as_view(), name='reservation_detail'),
    path('reservations/<uuid:pk>/update/', reservation.ReservationUpdateView.as_view(), name='reservation_update'),
    path('reservations/<uuid:pk>/delete/', reservation.ReservationDeleteView.as_view(), name='reservation_delete'),
    path('reservations/<uuid:pk>/fulfill/', reservation.ReservationFulfillView.as_view(), name='reservation_fulfill'),
    path('reservations/<uuid:pk>/cancel/', reservation.ReservationCancelView.as_view(), name='reservation_cancel'),
    
    # Export URLs
     path('reservations/export/', reservation.ReservationExportView.as_view(), name='reservation_export'),
    path('reservations/<uuid:pk>/export/', reservation.ReservationDetailExportView.as_view(), name='reservation_detail_export'),
    
    # API URLs
    path('reservations/<uuid:pk>/details/', reservation.get_reservation_details, name='reservation_details_api'),

    # Search
    path('search/', views.LibrarySearchView.as_view(), name='search'),
  
   
]