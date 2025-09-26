import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from datetime import date, timedelta


class Vehicle(models.Model):
    VEHICLE_TYPES = (
        ('bus', 'Bus'),
        ('van', 'Van'),
        ('car', 'Car'),
        ('minibus', 'Mini Bus'),
    )
    
    FUEL_TYPES = (
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('cng', 'CNG'),
        ('electric', 'Electric'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    vehicle_number = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField()
    color = models.CharField(max_length=30)
    capacity = models.IntegerField()
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPES)
    insurance_number = models.CharField(max_length=100, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    registration_date = models.DateField()
    registration_expiry = models.DateField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transport_vehicle'
    
    def __str__(self):
        return f"{self.vehicle_number} - {self.make} {self.model}"

class Driver(models.Model):
    LICENSE_TYPE_CHOICES = [
        ('LMV', 'Light Motor Vehicle'),
        ('HMV', 'Heavy Motor Vehicle'),
        ('MC', 'Motorcycle'),
        ('OTH', 'Other'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='driver_profile')
    license_number = models.CharField(max_length=50, unique=True)
    license_type = models.CharField(
        max_length=20,
        choices=LICENSE_TYPE_CHOICES,
        default='LMV'
    )
    license_expiry = models.DateField()
    experience = models.IntegerField(help_text="Years of experience")
    address = models.TextField()
    emergency_contact = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    # New fields for photos
    photo = models.ImageField(
        upload_to='drivers/photos/', 
        blank=True, 
        null=True,
        help_text="Driver's photo"
    )
    id_proof = models.ImageField(
        upload_to='drivers/id_proofs/', 
        blank=True, 
        null=True,
        help_text="Driver's ID proof photo"
    )
    license_photo = models.ImageField(
        upload_to='drivers/license_photos/', 
        blank=True, 
        null=True,
        help_text="Driver's license photo"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transport_driver'
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.license_number})"

    def license_status(self):
        """
        Returns the status of the license:
        - 'expired' if date is in the past
        - 'expiring' if within 30 days
        - 'valid' if more than 30 days remaining
        """
        if not self.license_expiry:
            return "not_set"
        today = date.today()
        if self.license_expiry < today:
            return "expired"
        elif self.license_expiry <= today + timedelta(days=30):
            return "expiring"
        return "valid"
   

class Route(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    start_point = models.CharField(max_length=200)
    end_point = models.CharField(max_length=200)
    distance = models.DecimalField(max_digits=6, decimal_places=2, help_text="Distance in km")
    estimated_time = models.DurationField(help_text="Estimated travel time")
    fare = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transport_route'
    
    def __str__(self):
        return f"{self.name} ({self.start_point} to {self.end_point})"

class RouteStop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    name = models.CharField(max_length=100)
    address = models.TextField()
    sequence = models.IntegerField()
    pickup_time = models.TimeField()
    drop_time = models.TimeField()
    
    class Meta:
        db_table = 'transport_route_stop'
        ordering = ['route', 'sequence']
    
    def __str__(self):
        return f"{self.route.name} - {self.name}"

class TransportAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transport_assignment'
    
    def __str__(self):
        return f"{self.vehicle.vehicle_number} - {self.route.name} - {self.driver}"

    @property
    def current_status(self):
        today = timezone.now().date()
        if not self.is_active:
            return "inactive"
        elif self.end_date and today > self.end_date:
            return "expired"
        elif today < self.start_date:
            return "scheduled"
        else:
            return "active"

class StudentTransport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    transport_assignment = models.ForeignKey(TransportAssignment, on_delete=models.CASCADE)
    pickup_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name='pickup_students')
    drop_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name='drop_students')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transport_student_transport'
        unique_together = ['student', 'start_date']
    
    def __str__(self):
        return f"{self.student} - {self.transport_assignment}"

class TransportAttendance(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    student_transport = models.ForeignKey(StudentTransport, on_delete=models.CASCADE)
    date = models.DateField()
    pickup_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    drop_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    pickup_time = models.TimeField(null=True, blank=True)
    drop_time = models.TimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    recorded_by = models.ForeignKey('users.User', on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transport_attendance'
        unique_together = ['student_transport', 'date']
    
    def __str__(self):
        return f"{self.student_transport.student} - {self.date}"

class MaintenanceRecord(models.Model):
    MAINTENANCE_TYPES = (
        ('routine', 'Routine Maintenance'),
        ('repair', 'Repair'),
        ('breakdown', 'Breakdown'),
        ('accident', 'Accident Repair'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPES)
    date = models.DateField()
    odometer_reading = models.IntegerField()
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    garage = models.CharField(max_length=200, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    next_due_reading = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transport_maintenance'
    
    def __str__(self):
        return f"{self.vehicle.vehicle_number} - {self.get_maintenance_type_display()} - {self.date}"