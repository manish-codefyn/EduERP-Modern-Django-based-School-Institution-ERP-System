import uuid
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum


class FeeStructure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE)
    class_name = models.ForeignKey('academics.Class', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finance_fee_structure'
        unique_together = ['institution', 'academic_year', 'class_name']

    def __str__(self):
        return f"{self.name} - {self.class_name} ({self.academic_year})"


class FeeInvoice(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('cancelled', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE)
    issue_date = models.DateField()
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finance_fee_invoice'
        indexes = [
            models.Index(fields=['institution', 'student']),
            models.Index(fields=['due_date', 'status']),
        ]

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.student}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            year = timezone.now().year
            month = timezone.now().month
            last_invoice = FeeInvoice.objects.filter(
                institution=self.institution,
                invoice_number__startswith=f"INV-{year}-{month:02d}-"
            ).order_by('-invoice_number').first()

            if last_invoice:
                last_num = int(last_invoice.invoice_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1

            self.invoice_number = f"INV-{year}-{month:02d}-{new_num:04d}"

        # Auto update status
        if self.paid_amount >= self.total_amount:
            self.status = 'paid'
        elif self.paid_amount > 0:
            self.status = 'partial'

        super().save(*args, **kwargs)
        
    @property
    def overdue(self) -> bool:
        """Check if invoice is overdue (unpaid and past due date)"""
        return self.status not in ['paid', 'cancelled'] and self.due_date < timezone.now().date()  
          
    @property
    def balance(self) -> Decimal:
        """Remaining balance for the invoice"""
        return max(Decimal(self.total_amount) - Decimal(self.paid_amount), Decimal("0.00"))

    @property
    def balance_display(self) -> str:
        """Formatted balance for UI"""
        return f"{self.balance:.2f}"


class Payment(models.Model):
    MODE_CHOICES = (
        ("cash", _("Cash")),
        ("cheque", _("Cheque")),
        ("bank_transfer", _("Bank Transfer")),
        ("online", _("Online Payment")),
    )

    STATUS_CHOICES = (
        ("pending", _("Pending")),
        ("partially_paid", _("Partially Paid")),
        ("paid", _("Paid")),
        ("overdue", _("Overdue")),
        ("failed", _("Failed")),
        ("refunded", _("Refunded")),
        ("cancelled", _("Cancelled")),
        ("completed", _("Completed")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="payments",
        null=True, blank=True, verbose_name=_("Student")
    )
    institution = models.ForeignKey(
        "organization.Institution", on_delete=models.CASCADE, related_name="payments",
        verbose_name=_("Institution")
    )
    invoice = models.ForeignKey(
        FeeInvoice, on_delete=models.CASCADE, related_name="payments",
        null=True, blank=True, verbose_name=_("Invoice")
    )
    payment_number = models.CharField(max_length=50, unique=True, blank=True, verbose_name=_("Payment Number"))
    payment_mode = models.CharField(max_length=20, choices=MODE_CHOICES, verbose_name=_("Payment Mode"))
    payment_date = models.DateField(default=timezone.now, verbose_name=_("Payment Date"))
    reference_number = models.CharField(max_length=100, blank=True, verbose_name=_("Reference Number"))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Total Amount"))
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Amount Paid"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name=_("Status"))
    remarks = models.TextField(blank=True, verbose_name=_("Remarks"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "finance_payment"
        ordering = ["-created_at"]
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        indexes = [
            models.Index(fields=["payment_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["payment_date"]),
        ]

    def __str__(self):
        return f"{self.payment_number} - {self.amount} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.payment_number:
            year = timezone.now().year
            month = timezone.now().month
            prefix = f"PAY-{year}-{month:02d}-"
            last_payment = Payment.objects.filter(payment_number__startswith=prefix).order_by("payment_number").last()
            if last_payment:
                last_number = int(last_payment.payment_number.split("-")[-1])
                self.payment_number = f"{prefix}{last_number + 1:04d}"
            else:
                self.payment_number = f"{prefix}0001"

        super().save(*args, **kwargs)

        # Update linked invoice balance atomically
        if self.invoice and self.status in ["completed", "paid", "partially_paid"]:
            with transaction.atomic():
                invoice = type(self.invoice).objects.select_for_update().get(pk=self.invoice.pk)
                invoice.paid_amount += self.amount_paid
                if invoice.paid_amount >= invoice.total_amount:
                    invoice.status = "paid"
                elif invoice.paid_amount > 0:
                    invoice.status = "partially_paid"
                invoice.save()

    def formatted_payment_date(self):
        """
        Returns payment_date formatted as dd-mm-yy (e.g., 14-10-25).
        """
        if self.payment_date:
            return self.payment_date.strftime("%d-%m-%y")
        return None
    
    @property
    def is_fully_paid(self):
        return self.status in ["paid", "completed"]
 
    @property
    def balance(self):
        return float(self.amount) - float(self.amount_paid)

    def balance_display(self):
        return f"{self.balance():.2f}"

    # Single payment formatted fields
    def amount_display(self):
        return f"{self.amount:.2f}"

    def amount_paid_display(self):
        return f"{self.amount_paid:.2f}"

    #  Total payments for a student
    @classmethod
    def total_for_student(cls, student):
        result = cls.objects.filter(student=student).aggregate(
            total=Sum("amount"), paid=Sum("amount_paid")
        )
        total = result["total"] or 0
        paid = result["paid"] or 0
        return {
            "total": f"{total:.2f}",
            "paid": f"{paid:.2f}",
            "balance": f"{(total - paid):.2f}",
        }

    #  Total payments for an institution
    @classmethod
    def total_for_institution(cls, institution):
        result = cls.objects.filter(institution=institution).aggregate(
            total=Sum("amount"), paid=Sum("amount_paid")
        )
        total = result["total"] or 0
        paid = result["paid"] or 0
        return {
            "total": f"{total:.2f}",
            "paid": f"{paid:.2f}",
            "balance": f"{(total - paid):.2f}",
        }


    # ---------------------------
    #  Instance helpers
    # ---------------------------
    def formatted_payment_date(self):
        """Returns payment_date formatted as dd-mm-yy (e.g., 14-10-25)."""
        if self.payment_date:
            return self.payment_date.strftime("%d-%m-%y")
        return None

    @property
    def is_fully_paid(self):
        return self.status in ["paid", "completed"]

    @property
    def balance(self):
        return float(self.amount) - float(self.amount_paid)

    def balance_display(self):
        return f"{self.balance:.2f}"

    def amount_display(self):
        return f"{self.amount:.2f}"

    def amount_paid_display(self):
        return f"{self.amount_paid:.2f}"

    def payment_mode_display(self):
        return self.get_payment_mode_display()

    def status_display(self):
        return self.get_status_display()

    # ---------------------------
    #  helpers
    # ---------------------------

    @classmethod
    def totals_by_mode(cls, institution):
        """Grouped totals by payment mode"""
        return (
            cls.objects.filter(institution=institution)
            .values("payment_mode")
            .annotate(total_amount=Sum("amount_paid"), count=Count("id"))
        )

    @classmethod
    def totals_by_status(cls, institution):
        """Grouped totals by payment status"""
        return (
            cls.objects.filter(institution=institution)
            .values("status")
            .annotate(total_amount=Sum("amount_paid"), count=Count("id"))
        )

    @classmethod
    def payments_in_range(cls, institution, start_date, end_date):
        """Payments for an institution in a date range"""
        return cls.objects.filter(
            institution=institution,
            payment_date__range=(start_date, end_date)
        )

    @classmethod
    def latest_for_student(cls, student):
        """Latest payment for a student"""
        return cls.objects.filter(student=student).order_by("-payment_date").first()

    @classmethod
    def overdue_payments(cls, institution):
        """Fetch overdue payments for an institution"""
        return cls.objects.filter(institution=institution, status="overdue")