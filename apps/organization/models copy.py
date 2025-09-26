import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class Institution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=50, unique=True)
    code = models.CharField(max_length=20, unique=True)

    # Type
    type = models.CharField(
        max_length=20,
        choices=[
            ("school", "School"),
            ("college", "College"),
            ("university", "University"),
            ("institute", "Institute"),
        ],
        default="school"
    )

    # Contact info
    address = models.TextField()
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)

    # Branding
    logo = models.ImageField(upload_to="institution_logos/", blank=True, null=True)
    stamp = models.ImageField(upload_to="institution_logos/", blank=True, null=True)

    # Settings
    timezone = models.CharField(max_length=50, default="UTC")
    fiscal_year_start = models.DateField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organization_institution"

    def __str__(self):
        return self.name


#  Legal / Compliance
class InstitutionCompliance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.OneToOneField(Institution, on_delete=models.CASCADE, related_name="compliance")

    gst_number = models.CharField(max_length=20, blank=True, null=True)
    pan_number = models.CharField(max_length=20, blank=True, null=True)
    tan_number = models.CharField(max_length=20, blank=True, null=True)

    registration_no = models.CharField(max_length=100, blank=True, null=True)
    registration_authority = models.CharField(max_length=255, blank=True, null=True)

    pf_registration_no = models.CharField(max_length=50, blank=True, null=True)  # Provident Fund
    esi_registration_no = models.CharField(max_length=50, blank=True, null=True) # Employee State Insurance

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

    class Meta:
        db_table = "organization_affiliation"

    def __str__(self):
        return f"{self.name} ({self.institution.name})"


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

    class Meta:
        db_table = "organization_accreditation"

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
            ("other", "Other"),
        ],
        default="other"
    )
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    document = models.FileField(upload_to="partnership_docs/", blank=True, null=True)

    class Meta:
        db_table = "organization_partnership"

    def __str__(self):
        return f"{self.partner_name} - {self.institution.name}"
