import uuid
import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import xlsxwriter


class ReportService:
    def __init__(self, school):
        self.school = school

    def generate_fee_report(self, start_date, end_date, format='pdf'):
        """Generate fee collection report"""
        from finance.models import Payment

        payments = Payment.objects.filter(
            school=self.school,
            payment_date__range=[start_date, end_date],
            status='completed'
        ).select_related('invoice__student')

        # Prepare data
        data = []
        total_amount = 0

        for payment in payments:
            data.append({
                'date': payment.payment_date,
                'receipt_no': payment.payment_number,
                'student': payment.invoice.student.user.get_full_name(),
                'admission_no': payment.invoice.student.admission_number,
                'class': payment.invoice.student.current_class.name,
                'amount': payment.amount,
                'mode': payment.get_payment_mode_display(),
            })
            total_amount += payment.amount

        context = {
            'school': self.school,
            'start_date': start_date,
            'end_date': end_date,
            'payments': data,
            'total_amount': total_amount,
        }

        if format == 'pdf':
            return self._generate_pdf('reports/fee_report.html', context, 'fee_report.pdf')
        elif format == 'excel':
            return self._generate_excel(data, 'fee_report.xlsx')
        elif format == 'csv':
            return self._generate_csv(data, 'fee_report.csv')

    def generate_student_report_card(self, student_id, exam_id, format='pdf'):
        """Generate student report card"""
        from students.models import Student
        from examination.models import ExamResult

        student = Student.objects.get(id=student_id, school=self.school)
        results = ExamResult.objects.filter(
            exam_subject__exam_id=exam_id,
            student=student
        ).select_related('exam_subject__subject')

        # Calculate totals and percentage
        total_marks = sum([r.marks_obtained for r in results])
        max_marks = sum([r.exam_subject.max_marks for r in results])
        percentage = (total_marks / max_marks) * 100 if max_marks > 0 else 0

        context = {
            'school': self.school,
            'student': student,
            'results': results,
            'total_marks': total_marks,
            'max_marks': max_marks,
            'percentage': percentage,
        }

        if format == 'pdf':
            return self._generate_pdf('reports/report_card.html', context, 'report_card.pdf')
        else:
            raise ValueError("Only PDF format is supported for report cards")

    def _generate_pdf(self, template, context, filename):
        """Generate PDF using xhtml2pdf"""
        html_string = render_to_string(template, context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Generate PDF
        pisa_status = pisa.CreatePDF(
            html_string,
            dest=response,
            encoding='utf-8'
        )

        if pisa_status.err:
            return HttpResponse("Error generating PDF", status=500)

        return response

    def _generate_excel(self, data, filename):
        """Generate Excel file from data"""
        output = BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='Report', index=False)

            # Auto-adjust columns width
            for column in df:
                column_width = max(df[column].astype(str).map(len).max(), len(column))
                col_idx = df.columns.get_loc(column)
                writer.sheets['Report'].set_column(col_idx, col_idx, column_width)

        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    def _generate_csv(self, data, filename):
        """Generate CSV file from data"""
        df = pd.DataFrame(data)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        df.to_csv(response, index=False)

        return response
