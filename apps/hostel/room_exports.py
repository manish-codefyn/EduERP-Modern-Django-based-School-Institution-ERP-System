from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import HttpResponse
from django.utils import timezone
from io import StringIO, BytesIO
import csv
import xlsxwriter

from apps.core.mixins import FinanceAccessRequiredMixin
from apps.core.utils import get_user_institution
from utils.utils import render_to_pdf, export_pdf_response
from .models import Room  # Import your Room model

class RoomExportView(FinanceAccessRequiredMixin, View):
    """
    Export Room data in CSV, PDF, Excel formats
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        hostel_id = request.GET.get("hostel")
        room_type = request.GET.get("room_type")
        floor = request.GET.get("floor")
        availability = request.GET.get("availability")  # available/unavailable
        maintenance = request.GET.get("maintenance")  # required/not_required

        institution = get_user_institution(request.user)
        qs = Room.objects.filter(hostel__institution=institution)

        if hostel_id:
            qs = qs.filter(hostel_id=hostel_id)

        if room_type:
            qs = qs.filter(room_type=room_type)

        if floor:
            qs = qs.filter(floor=floor)

        if availability:
            if availability.lower() == "available":
                qs = qs.filter(is_available=True)
            elif availability.lower() == "unavailable":
                qs = qs.filter(is_available=False)

        if maintenance:
            if maintenance.lower() == "required":
                qs = qs.filter(maintenance_required=True)
            elif maintenance.lower() == "not_required":
                qs = qs.filter(maintenance_required=False)

        qs = qs.order_by("hostel", "floor", "room_number")

        # Build filename
        filename_parts = ["rooms"]
        if hostel_id:
            filename_parts.append(f"hostel_{hostel_id}")
        if room_type:
            filename_parts.append(room_type)
        if floor:
            filename_parts.append(f"floor_{floor}")
        filename = "_".join(filename_parts).lower()

        # Prepare rows
        rows = []
        for room in qs:
            # Get amenities as comma-separated string
            amenities = ", ".join([amenity.name for amenity in room.amenities.all()])
            
            rows.append({
                "hostel": room.hostel.name,
                "room_number": room.room_number,
                "floor": room.floor,
                "room_type": room.get_room_type_display(),
                "capacity": room.capacity,
                "current_occupancy": room.current_occupancy,
                "available_beds": room.capacity - room.current_occupancy,
                "amenities": amenities,
                "is_available": "Yes" if room.is_available else "No",
                "maintenance_required": "Yes" if room.maintenance_required else "No",
                "maintenance_notes": room.maintenance_notes,
                "created_at": room.created_at.strftime("%Y-%m-%d %H:%M"),
            })

        organization = institution

        if fmt == "csv":
            return self.export_csv(rows, filename, organization)

        elif fmt == "pdf":
            return self.export_pdf(rows, filename, organization, qs.count())

        elif fmt == "excel":
            return self.export_excel(rows, filename, organization)

        return HttpResponse("Invalid format. Use csv, pdf, excel.", status=400)

    def export_csv(self, rows, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        writer.writerow([
            "Hostel", "Room Number", "Floor", "Type", "Capacity", 
            "Occupied", "Available Beds", "Amenities", "Available",
            "Maintenance Required", "Maintenance Notes", "Created At"
        ])

        for row in rows:
            writer.writerow([
                row['hostel'], row['room_number'], row['floor'], 
                row['room_type'], row['capacity'], row['current_occupancy'],
                row['available_beds'], row['amenities'], row['is_available'],
                row['maintenance_required'], row['maintenance_notes'], row['created_at']
            ])

        writer.writerow([])
        writer.writerow(["Total Rooms:", len(rows)])
        writer.writerow(["Organization:", organization.name if organization else "N/A"])
        writer.writerow(["Export Date:", timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_pdf(self, rows, filename, organization, total_count):
        context = {
            "rooms": rows,
            "total_count": total_count,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Room Export",
            "columns": [
                {"name": "Hostel", "width": "15%"},
                {"name": "Room No.", "width": "10%"},
                {"name": "Floor", "width": "5%"},
                {"name": "Type", "width": "10%"},
                {"name": "Capacity", "width": "8%"},
                {"name": "Occupied", "width": "8%"},
                {"name": "Available", "width": "8%"},
                {"name": "Amenities", "width": "15%"},
                {"name": "Status", "width": "8%"},
                {"name": "Maintenance", "width": "8%"},
            ]
        }

        pdf_bytes = render_to_pdf("hostel/export/rooms_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            ws = workbook.add_worksheet("Rooms")

            header_fmt = workbook.add_format({"bold": True, "bg_color": "#3b5998", "font_color": "white"})

            headers = [
                "Hostel", "Room Number", "Floor", "Type", "Capacity", 
                "Occupied", "Available Beds", "Amenities", "Available",
                "Maintenance Required", "Maintenance Notes", "Created At"
            ]

            for col, h in enumerate(headers):
                ws.write(0, col, h, header_fmt)

            for i, r in enumerate(rows, start=1):
                ws.write(i, 0, r['hostel'])
                ws.write(i, 1, r['room_number'])
                ws.write(i, 2, r['floor'])
                ws.write(i, 3, r['room_type'])
                ws.write(i, 4, r['capacity'])
                ws.write(i, 5, r['current_occupancy'])
                ws.write(i, 6, r['available_beds'])
                ws.write(i, 7, r['amenities'])
                ws.write(i, 8, r['is_available'])
                ws.write(i, 9, r['maintenance_required'])
                ws.write(i, 10, r['maintenance_notes'])
                ws.write(i, 11, r['created_at'])

            ws.set_column("A:L", 15)  # Set column widths
            ws.set_column("G:G", 12)  # Available Beds slightly wider
            ws.set_column("H:H", 25)  # Amenities column wider
            ws.set_column("K:K", 20)  # Maintenance Notes column wider

            summary_row = len(rows) + 2
            ws.write(summary_row, 0, "Total Rooms:")
            ws.write(summary_row, 1, len(rows))
            ws.write(summary_row + 1, 0, "Organization:")
            ws.write(summary_row + 1, 1, organization.name if organization else "N/A")
            ws.write(summary_row + 2, 0, "Export Date:")
            ws.write(summary_row + 2, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response