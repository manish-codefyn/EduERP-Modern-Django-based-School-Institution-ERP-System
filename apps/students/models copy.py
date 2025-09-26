import uuid
import os
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.urls import reverse

# Phone regex for validation
phone_regex = RegexValidator(
    regex=r"^\+?1?\d{9,15}$",
    message=_("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."),
)

# -------------------- Student Core --------------------
class Student(models.Model):
    STATUS_CHOICES = (
        ("ACTIVE", _("Active")),
        ("INACTIVE", _("Inactive")),
        ("ALUMNI", _("Alumni")),
        ("SUSPENDED", _("Suspended")),
        ("WITHDRAWN", _("Withdrawn")),
    )
    ADMISSION_TYPE_CHOICES = (
        ("REGULAR", _("Regular")),
        ("TRANSFER", _("Transfer")),
        ("LATERAL", _("Lateral Entry")),
    )
    GENDER_CHOICES = (
        ("M", _("Male")),
        ("F", _("Female")),
        ("O", _("Other")),
        ("U", _("Undisclosed")),
    )
    BLOOD_GROUP_CHOICES = (
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
        ("O+", "O+"),
        ("O-", "O-"),
    )
    CATEGORY_CHOICES = (
        ("", _("General")),
        ("SC", _("Scheduled Caste")),
        ("ST", _("Scheduled Tribe")),
        ("OBC", _("Other Backward Class")),
        ("OTHER", _("Other")),
    )
    RELIGION_CHOICES = (
        ("HINDU", _("Hindu")),
        ("MUSLIM", _("Muslim")),
        ("CHRISTIAN", _("Christian")),
        ("SIKH", _("Sikh")),
        ("BUDDHIST", _("Buddhist")),
        ("JAIN", _("Jain")),
        ("OTHER", _("Other")),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "users.User",
        on_delete=models.SET_NULL,  
        related_name="student_profile",
        null=True,                  
        blank=True      
    )  
    institution = models.ForeignKey("organization.Institution", on_delete=models.CASCADE, related_name="students")

    first_name = models.CharField(max_length=50, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=50, verbose_name=_("Last Name"))
    email = models.EmailField(verbose_name=_("Email Address"))
    mobile = models.CharField(max_length=17, validators=[phone_regex], verbose_name=_("Mobile Number"))
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True)
    religion = models.CharField(
        max_length=20, 
        choices=RELIGION_CHOICES, 
        blank=True,
        verbose_name=_("Religion")
    )
    admission_number = models.CharField(max_length=50, unique=True, blank=True, verbose_name=_("Admission Number"))
    roll_number = models.CharField(max_length=50, blank=True, verbose_name=_("Roll Number"))
    enrollment_date = models.DateField(default=timezone.now, verbose_name=_("Enrollment Date"))
    admission_type = models.CharField(
        max_length=20, 
        choices=ADMISSION_TYPE_CHOICES, 
        default="REGULAR",
        verbose_name=_("Admission Type")
    )

    date_of_birth = models.DateField(verbose_name=_("Date of Birth"))
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name=_("Gender"))
    blood_group = models.CharField(
        max_length=3, 
        choices=BLOOD_GROUP_CHOICES, 
        blank=True,
        verbose_name=_("Blood Group")
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="ACTIVE",
        verbose_name=_("Status")
    )

    academic_year = models.ForeignKey(
        "academics.AcademicYear", 
        on_delete=models.CASCADE, 
        related_name="students",
        verbose_name=_("Academic Year")
    )
    current_class = models.ForeignKey(
        "academics.Class", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="students",
        verbose_name=_("Current Class")
    )
    section = models.ForeignKey(
        "academics.Section", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="students",
        verbose_name=_("Section")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "students_student"
        ordering = ["first_name", "last_name"]
        verbose_name = _("Student")
        verbose_name_plural = _("Students")
        indexes = [
            models.Index(fields=['admission_number']),
            models.Index(fields=['roll_number']),
            models.Index(fields=['email']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.admission_number} - {self.first_name} {self.last_name}"

    def get_absolute_url(self):
        return reverse('students:student_detail', kwargs={'pk': self.pk})
    
    def get_document(self, doc_type):
        """Return the first document of the given type, or None."""
        return self.documents.filter(doc_type=doc_type).first()    
    
    def get_photo(self):
        """Return student's photo document or None"""
        return self.documents.filter(doc_type="PHOTO").first()

    def get_birth_certificate(self):
        return self.get_document("BIRTH_CERTIFICATE")

    def get_aadhaar(self):
        return self.get_document("AADHAAR")

    def get_previous_marksheet(self):
        return self.get_document("PREVIOUS_MARKSHEET")

    def get_transfer_certificate(self):
        return self.get_document("TRANSFER_CERTIFICATE")

    def get_medical_certificate(self):
        return self.get_document("MEDICAL_CERTIFICATE")

    def get_caste_certificate(self):
        return self.get_document("CASTE_CERTIFICATE")

    def get_income_certificate(self):
        return self.get_document("INCOME_CERTIFICATE")

    def get_other_document(self):
        return self.get_document("OTHER")
    
    def clean(self):
        """Custom validation for the model"""
        errors = {}
        today = timezone.now().date()

        # Convert datetime to date if necessary
        dob = self.date_of_birth
        if isinstance(dob, timezone.datetime):
            dob = dob.date()
        enroll_date = self.enrollment_date
        if isinstance(enroll_date, timezone.datetime):
            enroll_date = enroll_date.date()

        # Check if enrollment date is not in the future
        if enroll_date and enroll_date > today:
            errors['enrollment_date'] = _("Enrollment date cannot be in the future")

        # Check if date of birth is valid
        if dob and dob >= today:
            errors['date_of_birth'] = _("Date of birth must be in the past")

        # Check if student is at least 3 years old
        if dob:
            age_years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age_years < 3:
                errors['date_of_birth'] = _("Student must be at least 3 years old")

        # Check if section belongs to the selected class
        if self.section and self.current_class and self.section.class_name != self.current_class:
            errors['section'] = _("Selected section does not belong to the selected class")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Custom save method with automatic admission number generation"""
        if not self.admission_number:
            # Generate admission number if not provided
            prefix = f"ADM-{timezone.now().year}-"
            last_student = Student.objects.filter(
                admission_number__startswith=prefix
            ).order_by('admission_number').last()
            
            if last_student:
                last_number = int(last_student.admission_number.split('-')[-1])
                self.admission_number = f"{prefix}{last_number + 1:04d}"
            else:
                self.admission_number = f"{prefix}0001"
                
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def fee_status(self):
        """Check latest fee payment status from finance app"""
        latest_payment = self.payments.order_by("-created_at").first()
        if not latest_payment:
            return _("No Payment Record")
        return latest_payment.status
    
    @property
    def father(self):
        return self.guardians.filter(relation="FATHER").first()

    @property
    def mother(self):
        return self.guardians.filter(relation="MOTHER").first()
    
    @property
    def permanent_address(self):
        """Returns the formatted permanent address of the student"""
        address = self.addresses.filter(address_type="PERMANENT").first()
        if not address:
            return ""
        lines = [address.address_line1]
        if address.address_line2:
            lines.append(address.address_line2)
        lines.append(f"{address.city}, {address.state} - {address.pincode}")
        lines.append(address.country)
        return ", ".join(lines)

    @property
    def current_address(self):
        """Returns the formatted current/correspondence address of the student"""
        address = self.addresses.filter(is_current=True).first()
        if not address:
            return ""
        lines = [address.address_line1]
        if address.address_line2:
            lines.append(address.address_line2)
        lines.append(f"{address.city}, {address.state} - {address.pincode}")
        lines.append(address.country)
        return ", ".join(lines)
        
# -------------------- Guardian --------------------
class Guardian(models.Model):
    RELATION_CHOICES = (
        ("FATHER", _("Father")),
        ("MOTHER", _("Mother")),
        ("GUARDIAN", _("Guardian")),
        ("GRANDFATHER", _("Grandfather")),
        ("GRANDMOTHER", _("Grandmother")),
        ("UNCLE", _("Uncle")),
        ("AUNT", _("Aunt")),
        ("BROTHER", _("Brother")),
        ("SISTER", _("Sister")),
        ("OTHER", _("Other")),
    )
    OCCUPATION_CHOICES = (
        ("SERVICE", _("Service")),
        ("BUSINESS", _("Business")),
        ("GOVT", _("Government Job")),
        ("RETIRED", _("Retired")),
        ("HOUSEWIFE", _("Housewife")),
        ("FARMER", _("Farmer")),
        ("STUDENT", _("Student")),
        ("UNEMPLOYED", _("Unemployed")),
        ("OTHER", _("Other")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name="guardians",
        verbose_name=_("Student")
    )
    relation = models.CharField(
        max_length=20, 
        choices=RELATION_CHOICES,
        verbose_name=_("Relation")
    )
    name = models.CharField(max_length=100, verbose_name=_("Full Name"))
    occupation = models.CharField(
        max_length=20, 
        choices=OCCUPATION_CHOICES, 
        blank=True,
        verbose_name=_("Occupation")
    )
    phone = models.CharField(
        max_length=17, 
        validators=[phone_regex], 
        blank=True,
        verbose_name=_("Phone Number")
    )
    email = models.EmailField(blank=True, verbose_name=_("Email Address"))
    is_primary = models.BooleanField(
        default=False,
        verbose_name=_("Is Primary Guardian")
    )
    
    address = models.TextField(blank=True, verbose_name=_("Address"))
    city = models.CharField(max_length=100, blank=True, verbose_name=_("City"))
    state = models.CharField(max_length=100, blank=True, verbose_name=_("State"))
    pincode = models.CharField(max_length=10, blank=True, verbose_name=_("Pincode"))

    class Meta:
        db_table = "students_guardian"
        verbose_name = _("Guardian")
        verbose_name_plural = _("Guardians")
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'is_primary'],
                condition=models.Q(is_primary=True),
                name='unique_primary_guardian_per_student'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.relation}) - {self.student}"

    def clean(self):
        """Custom validation for the model"""
        # Ensure only one primary guardian per student
        if self.is_primary:
            existing_primary = Guardian.objects.filter(
                student=self.student, 
                is_primary=True
            ).exclude(id=self.id)
            
            if existing_primary.exists():
                raise ValidationError(_("This student already has a primary guardian"))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# -------------------- Medical --------------------
class StudentMedicalInfo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.OneToOneField(
        Student, 
        on_delete=models.CASCADE, 
        related_name="medical_info",
        verbose_name=_("Student")
    )
    conditions = models.TextField(
        blank=True,
        verbose_name=_("Medical Conditions"),
        help_text=_("List any chronic medical conditions")
    )
    allergies = models.TextField(
        blank=True,
        verbose_name=_("Allergies"),
        help_text=_("List any known allergies")
    )
    disability = models.BooleanField(
        default=False,
        verbose_name=_("Has Disability")
    )
    disability_type = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name=_("Disability Type")
    )
    disability_percentage = models.PositiveIntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name=_("Disability Percentage")
    )
    emergency_contact_name = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name=_("Emergency Contact Name")
    )
    emergency_contact_phone = models.CharField(
        max_length=17, 
        validators=[phone_regex], 
        blank=True,
        verbose_name=_("Emergency Contact Phone")
    )
    emergency_contact_relation = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name=_("Emergency Contact Relation")
    )

    class Meta:
        db_table = "students_medical_info"
        verbose_name = _("Medical Information")
        verbose_name_plural = _("Medical Information")

    def __str__(self):
        return f"Medical Info - {self.student}"

    def clean(self):
        if self.disability and not self.disability_type:
            raise ValidationError({
                'disability_type': _('Disability type is required when disability is marked')
            })
            
        if self.disability_percentage and not self.disability:
            raise ValidationError({
                'disability': _('Disability must be checked if disability percentage is provided')
            })


# -------------------- Address --------------------
class StudentAddress(models.Model):
    ADDRESS_TYPE_CHOICES = (
        ("PERMANENT", _("Permanent")),
        ("CORRESPONDENCE", _("Correspondence")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name="addresses",
        verbose_name=_("Student")
    )
    address_type = models.CharField(
        max_length=20, 
        choices=ADDRESS_TYPE_CHOICES,
        default="PERMANENT",
        verbose_name=_("Address Type")
    )
    address_line1 = models.CharField(max_length=255, verbose_name=_("Address Line 1"))
    address_line2 = models.CharField(max_length=255, blank=True, verbose_name=_("Address Line 2"))
    city = models.CharField(max_length=100, verbose_name=_("City"))
    state = models.CharField(max_length=100, verbose_name=_("State"))
    pincode = models.CharField(max_length=10, verbose_name=_("Pincode"))
    country = models.CharField(max_length=100, default="India", verbose_name=_("Country"))
    is_current = models.BooleanField(default=True, verbose_name=_("Is Current Address"))

    class Meta:
        db_table = "students_address"
        verbose_name = _("Student Address")
        verbose_name_plural = _("Student Addresses")
        unique_together = [['student', 'address_type']]

    def __str__(self):
        return f"{self.address_type} Address - {self.student}"


# -------------------- Documents --------------------
def student_document_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{slugify(instance.student.admission_number)}_{slugify(instance.doc_type)}.{ext}"
    return os.path.join("student_documents", str(instance.student.id), filename)



class StudentDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = (
        ("PHOTO", _("Photograph")),
        ("BIRTH_CERTIFICATE", _("Birth Certificate")),
        ("AADHAAR", _("Aadhaar Card")),
        ("PREVIOUS_MARKSHEET", _("Previous Marksheet")),
        ("TRANSFER_CERTIFICATE", _("Transfer Certificate")),
        ("MEDICAL_CERTIFICATE", _("Medical Certificate")),
        ("CASTE_CERTIFICATE", _("Caste Certificate")),
        ("INCOME_CERTIFICATE", _("Income Certificate")),
        ("OTHER", _("Other")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name="documents",
        verbose_name=_("Student")
    )
    doc_type = models.CharField(
        max_length=50, 
        choices=DOCUMENT_TYPE_CHOICES,
        verbose_name=_("Document Type")
    )
    file = models.FileField(
        upload_to=student_document_upload_path, 
        verbose_name=_("Document File")
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Uploaded At"))
    is_verified = models.BooleanField(default=False, verbose_name=_("Is Verified"))

    class Meta:
        db_table = "students_documents"
        verbose_name = _("Student Document")
        verbose_name_plural = _("Student Documents")

    def __str__(self):
        return f"{self.get_doc_type_display()} - {self.student}"

    def clean(self):
        # Limit file size to 5MB
        if self.file and self.file.size > 5 * 1024 * 1024:
            raise ValidationError({'file': _('File size must be less than 5MB')})


# -------------------- Transport --------------------
class StudentTransport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.OneToOneField(
        Student, 
        on_delete=models.CASCADE, 
        related_name="transport",
        verbose_name=_("Student")
    )
    route = models.ForeignKey(
        "transportation.Route", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Route")
    )
    pickup_point = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name=_("Pickup Point")
    )
    drop_point = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name=_("Drop Point")
    )
    transport_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name=_("Transport Fee")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    class Meta:
        db_table = "students_transport"
        verbose_name = _("Student Transport")
        verbose_name_plural = _("Student Transport")

    def __str__(self):
        return f"Transport - {self.student}"


# -------------------- Hostel --------------------
class StudentHostel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.OneToOneField(
        Student, 
        on_delete=models.CASCADE, 
        related_name="hostel",
        verbose_name=_("Student")
    )
    hostel = models.ForeignKey(
        "hostel.Hostel", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Hostel")
    )
    room_number = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name=_("Room Number")
    )
    check_in_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name=_("Check-in Date")
    )
    check_out_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name=_("Check-out Date")
    )
    hostel_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name=_("Hostel Fee")
    )

    class Meta:
        db_table = "students_hostel"
        verbose_name = _("Student Hostel")
        verbose_name_plural = _("Student Hostel")

    def __str__(self):
        return f"Hostel - {self.student}"

    def clean(self):
        if self.check_out_date and self.check_in_date and self.check_out_date <= self.check_in_date:
            raise ValidationError({
                'check_out_date': _('Check-out date must be after check-in date')
            })


# -------------------- Academic History --------------------
class StudentHistory(models.Model):
    RESULT_CHOICES = (
        ("PASS", _("Pass")),
        ("FAIL", _("Fail")),
        ("COMPARTMENT", _("Compartment")),
        ("APPEARING", _("Appearing")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name="history",
        verbose_name=_("Student")
    )
    academic_year = models.ForeignKey(
        "academics.AcademicYear", 
        on_delete=models.CASCADE,
        verbose_name=_("Academic Year")
    )
    class_name = models.ForeignKey(
        "academics.Class", 
        on_delete=models.CASCADE,
        verbose_name=_("Class")
    )
    section = models.ForeignKey(
        "academics.Section", 
        on_delete=models.CASCADE,
        verbose_name=_("Section")
    )
    roll_number = models.CharField(
        max_length=50,
        verbose_name=_("Roll Number")
    )
    final_grade = models.CharField(
        max_length=5, 
        blank=True,
        verbose_name=_("Final Grade")
    )
    percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Percentage")
    )
    result = models.CharField(
        max_length=20, 
        choices=RESULT_CHOICES,
        verbose_name=_("Result")
    )
    remarks = models.TextField(
        blank=True,
        verbose_name=_("Remarks")
    )
    promoted = models.BooleanField(
        default=True,
        verbose_name=_("Promoted")
    )
    previous_school = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name=_("Previous School")
    )
    previous_class = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name=_("Previous Class")
    )
    previous_marks = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Previous Marks")
    )
    transfer_reason = models.TextField(
        blank=True,
        verbose_name=_("Transfer Reason")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "students_student_history"
        unique_together = [["student", "academic_year"]]
        ordering = ["-academic_year__start_date"]
        verbose_name = _("Student Academic History")
        verbose_name_plural = _("Student Academic Histories")

    def __str__(self):
        return f"{self.student.admission_number} - {self.academic_year.name}"

    def clean(self):
        errors = {}
        
        if self.percentage is not None:
            if self.result == "PASS" and self.percentage < 33:
                errors['percentage'] = _('Percentage should be at least 33 for PASS result')
            elif self.result == "FAIL" and self.percentage >= 33:
                errors['result'] = _('Result should be PASS if percentage is 33 or above')

        # Check for unique roll number within the same class and academic year
        if StudentHistory.objects.filter(
            academic_year=self.academic_year,
            class_name=self.class_name,
            section=self.section,
            roll_number=self.roll_number
        ).exclude(id=self.id).exists():
            errors['roll_number'] = _('Roll number must be unique within the same class and academic year')
            
        if errors:
            raise ValidationError(errors)
        

class StudentIdentification(models.Model):
    student = models.OneToOneField(
        'Student',
        on_delete=models.CASCADE,
        related_name='identification',
        verbose_name=_("Student")
    )
    
    aadhaar_number = models.CharField(
        max_length=12, 
        blank=True, 
        null=True,
        unique=True,
        validators=[RegexValidator(regex=r'^\d{12}$', message=_('Aadhaar number must be 12 digits'))],
        verbose_name=_("Aadhaar Number")
    )
    abc_id = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        unique=True,
        verbose_name=_("ABC ID")
    )
    shiksha_id = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        unique=True,
        verbose_name=_("Shiksha ID")
    )
    
    # Additional identification fields
    pan_number = models.CharField(
        max_length=10, 
        blank=True, 
        null=True,
        unique=True,
        verbose_name=_("PAN Number")
    )
    passport_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        unique=True,
        verbose_name=_("Passport Number")
    )
    
    class Meta:
        verbose_name = _("Student Identification")
        verbose_name_plural = _("Student Identifications")
        db_table = 'student_identification'

    def __str__(self):
        return f"Identification for {self.student.full_name}"