import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from datetime import datetime

class Institution(models.Model):
    TYPE_CHOICES = [
        ("school", "School"),
        ("college", "College"),
        ("university", "University"),
        ("institute", "Institute"),
        ("training_center", "Training Center"),
    ]


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50, blank=True, null=True)
    slug = models.SlugField(max_length=50, unique=True)
    code = models.CharField(max_length=20, unique=True)
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="school"
    )
    # Contact info
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default="India")
    pincode = models.CharField(max_length=10, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True, null=True)

    # Branding
    logo = models.ImageField(upload_to="institution_logos/", blank=True, null=True)
    stamp = models.ImageField(upload_to="institution_stamps/", blank=True, null=True)
    favicon = models.ImageField(upload_to="institution_favicon/", blank=True, null=True)
    banner = models.ImageField(upload_to="institution_banners/", blank=True, null=True)
    # ID Card Colors - Individual fields for better UI
    primary_color = models.CharField(max_length=7, default='#0D47A1', 
                                   help_text="Primary color (e.g., #0D47A1)")
    secondary_color = models.CharField(max_length=7, default='#1976D2', 
                                     help_text="Secondary color (e.g., #1976D2)")
    accent_color = models.CharField(max_length=7, default='#42A5F5', 
                                  help_text="Accent color (e.g., #42A5F5)")
    text_dark_color = models.CharField(max_length=7, default='#212121', 
                                     help_text="Dark text color (e.g., #212121)")
    text_light_color = models.CharField(max_length=7, default='#FFFFFF', 
                                      help_text="Light text color (e.g., #FFFFFF)")
    text_muted_color = models.CharField(max_length=7, default='#757575', 
                                      help_text="Muted text color (e.g., #757575)")
    # Academic settings
    academic_year_start = models.DateField(blank=True, null=True)
    academic_year_end = models.DateField(blank=True, null=True)
    timezone = models.CharField(max_length=50, default="UTC")
    fiscal_year_start = models.DateField()
    language = models.CharField(max_length=50, default="English")
    currency = models.CharField(max_length=10, default="INR")
    
    # Status
    is_active = models.BooleanField(default=True)
    established_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organization_institution"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    
    def get_id_card_colors(self):
        """Return color configuration as a dictionary"""
        return {
            'primary': self.primary_color,
            'secondary': self.secondary_color,
            'accent': self.accent_color,
            'text_dark': self.text_dark_color,
            'text_light': self.text_light_color,
            'text_muted': self.text_muted_color,
        }

class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20)
    short_name = models.CharField(max_length=50, blank=True, null=True)
    
    # Department details
    department_type = models.CharField(
        max_length=20,
        choices=[
            ("academic", "Academic"),
            ("administrative", "Administrative"),
            ("support", "Support"),
            ("research", "Research"),
        ],
        default="academic"
    )
    
    description = models.TextField(blank=True, null=True)
    head_of_department = models.ForeignKey(
        'hr.Faculty', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        related_name="headed_departments"
    )
    
    # Contact info
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    office_location = models.CharField(max_length=100, blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    established_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organization_department"
        unique_together = ['institution', 'code']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.institution.name}"
    
  

class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20)
    
    # Branch details
    is_main_campus = models.BooleanField(default=False)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="India")
    pincode = models.CharField(max_length=10)
    
    # Contact info
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    # Managerial info
    branch_manager = models.ForeignKey(
        'hr.Staff', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        related_name="managed_branches"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    established_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organization_branch"
        unique_together = ['institution', 'code']
        verbose_name_plural = "Branches"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.institution.name}"


#  Legal / Compliance
class InstitutionCompliance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.OneToOneField(Institution, on_delete=models.CASCADE, related_name="compliance")

    gst_number = models.CharField(max_length=20, blank=True, null=True)
    pan_number = models.CharField(max_length=20, blank=True, null=True)
    tan_number = models.CharField(max_length=20, blank=True, null=True)

    registration_no = models.CharField(max_length=100, blank=True, null=True)
    registration_authority = models.CharField(max_length=255, blank=True, null=True)
    registration_date = models.DateField(blank=True, null=True)

    pf_registration_no = models.CharField(max_length=50, blank=True, null=True)  # Provident Fund
    esi_registration_no = models.CharField(max_length=50, blank=True, null=True) # Employee State Insurance
    
    # Educational specific compliance
    udise_code = models.CharField(max_length=20, blank=True, null=True)  # For schools in India
    aicte_code = models.CharField(max_length=20, blank=True, null=True)  # For technical institutions
    ugc_code = models.CharField(max_length=20, blank=True, null=True)    # For universities
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organization_institution_compliance"

    def __str__(self):
        return f"Compliance for {self.institution.name}"


#  Affiliations (CBSE, ICSE, UGC, AICTE, NAAC, etc.)
class Affiliation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="affiliations")

    name = models.CharField(max_length=255)  # e.g., "CBSE", "UGC", "AICTE"
    code = models.CharField(max_length=50, blank=True, null=True)
    valid_from = models.DateField(blank=True, null=True)
    valid_to = models.DateField(blank=True, null=True)
    document = models.FileField(upload_to="affiliation_docs/", blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    renewal_required = models.BooleanField(default=False)
    renewal_notice_period = models.PositiveIntegerField(
        default=90, 
        help_text="Days before expiry to send renewal notice"
    )

    class Meta:
        db_table = "organization_affiliation"
        ordering = ['-valid_from']

    def __str__(self):
        return f"{self.name} ({self.institution.name})"

    @property
    def days_until_expiry(self):
        """Calculate days until expiry"""
        if self.valid_to:
            return (self.valid_to - datetime.now().date()).days
        return None

    @property
    def is_expired(self):
        """Check if affiliation has expired"""
        if self.valid_to:
            return self.valid_to < datetime.now().date()
        return False

    @property
    def is_expiring_soon(self):
        """Check if affiliation is expiring soon (within renewal notice period)"""
        if self.valid_to and self.renewal_required:
            days_until_expiry = self.days_until_expiry
            return 0 <= days_until_expiry <= self.renewal_notice_period
        return False

    @property
    def validity_percentage(self):
        """Calculate percentage of validity period completed"""
        if self.valid_from and self.valid_to:
            total_days = (self.valid_to - self.valid_from).days
            if total_days > 0:
                days_passed = (datetime.now().date() - self.valid_from).days
                return min(max(0, int((days_passed / total_days) * 100)), 100)
        return 0
    
#  Accreditations (like NAAC grades, ISO certification, NBA)
class Accreditation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="accreditations")

    name = models.CharField(max_length=255)  # e.g., "NAAC", "ISO 9001", "NBA"
    grade_or_level = models.CharField(max_length=100, blank=True, null=True)  # e.g., "A++", "ISO 9001:2015"
    awarded_by = models.CharField(max_length=255, blank=True, null=True)
    valid_from = models.DateField(blank=True, null=True)
    valid_to = models.DateField(blank=True, null=True)
    certificate = models.FileField(upload_to="accreditation_certs/", blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    renewal_required = models.BooleanField(default=False)

    class Meta:
        db_table = "organization_accreditation"
        ordering = ['-valid_from']

    def __str__(self):
        return f"{self.name} ({self.institution.name})"


#  Tie-ups / MoUs / Partnerships
class Partnership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="partnerships")

    partner_name = models.CharField(max_length=255)
    partner_type = models.CharField(
        max_length=50,
        choices=[
            ("industry", "Industry"),
            ("ngo", "NGO"),
            ("government", "Government"),
            ("foreign_university", "Foreign University"),
            ("research_institute", "Research Institute"),
            ("other", "Other"),
        ],
        default="other"
    )
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    document = models.FileField(upload_to="partnership_docs/", blank=True, null=True)
    
    # Contact person
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    renewal_required = models.BooleanField(default=False)

    class Meta:
        db_table = "organization_partnership"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.partner_name} - {self.institution.name}"