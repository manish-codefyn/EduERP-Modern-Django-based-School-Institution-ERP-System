import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.organization.models import Institution
from apps.students.models import Student
from apps.hr.models import Staff
from django.contrib import messages
from django.urls import reverse

# Hostel Model
class Hostel(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('mixed', 'Mixed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True, help_text="Short code for the hostel")
    gender_type = models.CharField(max_length=10, choices=GENDER_CHOICES, default='mixed')
    capacity = models.PositiveIntegerField(default=0)
    current_occupancy = models.PositiveIntegerField(default=0, editable=False)
    warden = models.ForeignKey(
        Staff, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='managed_hostels'
    )
    assistant_warden = models.ForeignKey(
        Staff, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assistant_managed_hostels'
    )
    contact_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    facilities = models.ManyToManyField('HostelFacility', blank=True)
    monthly_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hostel_hostel"
        ordering = ["name"]
        unique_together = [('institution', 'name')]

    def __str__(self):
        return self.name
    
    def available_beds(self):
        return self.capacity - self.current_occupancy
    
    def occupancy_percentage(self):
        if self.capacity == 0:
            return 0
        return (self.current_occupancy / self.capacity) * 100


# Hostel Facility with institution
class HostelFacility(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='facilities')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class for UI representation")

    class Meta:
        db_table = "hostel_facility"
        ordering = ["name"]
        verbose_name_plural = "Hostel Facilities"

    def __str__(self):
        return self.name


# Room Model
class Room(models.Model):
    ROOM_TYPE_CHOICES = [
        ('single', 'Single'),
        ('double', 'Double'),
        ('triple', 'Triple'),
        ('dormitory', 'Dormitory'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name='rooms')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='rooms', editable=False)
    room_number = models.CharField(max_length=10)
    floor = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES, default='double')
    capacity = models.PositiveIntegerField(default=1)
    current_occupancy = models.PositiveIntegerField(default=0, editable=False)
    amenities = models.ManyToManyField('RoomAmenity', blank=True)
    is_available = models.BooleanField(default=True)
    maintenance_required = models.BooleanField(default=False)
    maintenance_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hostel_room"
        ordering = ["hostel", "floor", "room_number"]
        unique_together = [('hostel', 'room_number')]

    def __str__(self):
        return f"{self.hostel.name} - Room {self.room_number}"
    
    def available_beds(self):
        return self.capacity - self.current_occupancy


# Room Amenity
class RoomAmenity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='room_amenities')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "hostel_room_amenity"
        ordering = ["name"]
        verbose_name_plural = "Room Amenities"

    def __str__(self):
        return self.name


# Hostel Allocation
class HostelAllocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='hostel_allocations')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='allocations')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='hostel_allocations', editable=False)
    date_from = models.DateField()
    date_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hostel_allocation"
        ordering = ["-date_from", "student"]
        unique_together = [('student', 'is_active')]

    def __str__(self):
        return f"{self.student} - {self.room}"


# Hostel Fee Structure
class HostelFeeStructure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name='fee_structures')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='hostel_fee_structures', editable=False)
    room_type = models.CharField(max_length=20, choices=Room.ROOM_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(
        max_length=10, 
        choices=[('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')],
        default='monthly'
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hostel_fee_structure"
        ordering = ["hostel", "-effective_from"]

    def __str__(self):
        return f"{self.hostel.name} - {self.room_type} - {self.amount}"


# Hostel Attendance
class HostelAttendance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='hostel_attendance', editable=False)
    date = models.DateField()
    present = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hostel_attendance"
        unique_together = [('student', 'date')]


# Hostel Visitor Log
class HostelVisitorLog(models.Model):
    ID_PROOF_CHOICES = [
        ('', 'Select ID Proof'),
        ('aadhaar', 'Aadhaar Card'),
        ('voter', 'Voter ID'),
        ('driving', 'Driving License'),
        ('passport', 'Passport'),
        ('college', 'College ID'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor_name = models.CharField(max_length=100)
    student_visited = models.ForeignKey(Student, on_delete=models.CASCADE)
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name='hostel_visitor_logs',
        editable=False
    )
    purpose = models.CharField(max_length=200)
    id_proof = models.CharField(
        max_length=100,
        choices=ID_PROOF_CHOICES,
        blank=True
    )
    id_number = models.CharField(max_length=50, blank=True)
    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField(null=True, blank=True)
    recorded_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = "hostel_visitor_log"


# Hostel Inventory
class HostelInventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='hostel_inventory', editable=False)
    item_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=0)
    condition = models.CharField(max_length=20, choices=[
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ])
    last_maintenance = models.DateField(null=True, blank=True)
    next_maintenance = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "hostel_inventory"
        verbose_name_plural = "Hostel Inventory"

    def get_absolute_url(self):
        return reverse("hostel:inventory_detail", kwargs={"pk": self.pk})
    
    def save(self, *args, **kwargs):
        """
        Automatically populate institution from hostel if not set.
        """
        if self.hostel and not self.institution_id:
            self.institution = self.hostel.institution
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} ({self.hostel.name})"
    
    
# Maintenance Request
class MaintenanceRequest(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='maintenance_requests', editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)
    requested_by = models.ForeignKey(Staff, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    assigned_to = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_maintenance')
    requested_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "maintenance_request"
        
    def save(self, *args, **kwargs):
        # Auto-populate institution from hostel if not set
        if self.hostel and not self.institution_id:
            self.institution = self.hostel.institution
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.hostel} ({self.room})"