import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageColor
import qrcode
from django.conf import settings
from django.http import HttpResponse
from django.utils.encoding import force_str

# Gracefully handle the absence of the typing module in older Python versions
try:
    from typing import Tuple
except ImportError:
    Tuple = None


class FacultyIDCardGenerator:
    """
    Generates an elegant and professional ID card for a faculty member.

    This class builds upon a sophisticated design featuring a gradient background,
    dynamic geometric shapes, and a refined color palette, tailored specifically
    for academic staff.
    """
    # --- Configuration Constants for Easy Styling ---

    # Card Dimensions
    WIDTH, HEIGHT = 600, 900
    MARGIN = 20 # Increased margin for a cleaner look

    # A refined color palette for a prestigious, academic feel
    DEFAULT_COLORS = {
        'background_start': '#0B1D36', # Deeper Oxford Blue
        'background_end': '#1A3A69',   # Darker Imperial Blue
        'primary': '#48CAE4',          # Bright Cyan (for highlights)
        'primary_accent': '#00B4D8',   # Stronger Cyan
        'secondary': '#E0A800',        # Rich Gold/Amber (more academic than yellow)
        'text_light': '#F8F9FA',       # Off-White (softer than pure white)
        'text_dark': '#0B1D36',        # Match background for consistency
        'text_muted': '#ADC8E6',       # Light Steel Blue
    }

    # Font Awesome 6 Solid Icons, including new icons for academic details
    ICON_MAP = {
        'employee_id': '\uf2c1',    # ID Badge
        'designation': '\uf554',    # User Tie
        'department': '\uf0c0',     # Users
        'qualification': '\uf501',  # User Graduate
        'specialization': '\uf02d', # Book
        'phone': '\uf879',          # Phone Alt
    }

    def __init__(self, faculty, logo_path=None, stamp_path=None):
        """
        Initializes the generator for a specific faculty member.

        Args:
            faculty (Faculty): The Faculty model instance.
            logo_path (str, optional): Filesystem path to the institution's logo.
            stamp_path (str, optional): Filesystem path to the official stamp image.
        """
        self.faculty = faculty
        self.staff = faculty.staff  # Convenience access to the related Staff object
        self.logo_path = logo_path
        self.stamp_path = stamp_path
        self.colors = self._get_color_config()
        self._load_fonts()

    def _get_color_config(self):
        """Loads colors from Django settings, falling back to defaults."""
        if hasattr(settings, 'ID_CARD_COLORS'):
            return {**self.DEFAULT_COLORS, **settings.ID_CARD_COLORS}
        return self.DEFAULT_COLORS

    def _load_fonts(self):
        """
        Loads TrueType fonts from a predefined path.
        Falls back to a basic default font if custom fonts are not found.
        """
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            font_dir = os.path.join(base_dir, "static", "fonts")
            self.fonts = {
                'org_name': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Bold.ttf"), 28),
                'title': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Regular.ttf"), 18),
                'name': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Bold.ttf"), 40),
                'department': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Medium.ttf"), 24),
                'details_label': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-SemiBold.ttf"), 20),
                'details_value': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Regular.ttf"), 20),
                'footer': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Italic.ttf"), 16),
                'icon': ImageFont.truetype(os.path.join(font_dir, "Font Awesome 6 Free-Solid-900.ttf"), 22),
            }
        except (IOError, KeyError):
            # Fallback if custom fonts are missing
            default_font = ImageFont.load_default()
            font_keys = ['org_name', 'title', 'name', 'department', 'details_label', 'details_value', 'footer', 'icon']
            self.fonts = {key: default_font for key in font_keys}

    def _create_canvas(self) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
        """Creates the base image with a gradient background and decorative shapes."""
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT))
        draw = ImageDraw.Draw(img, 'RGBA') # Use RGBA for transparent shapes

        # Create a smooth vertical gradient
        start_color = ImageColor.getrgb(self.colors['background_start'])
        end_color = ImageColor.getrgb(self.colors['background_end'])
        for y in range(self.HEIGHT):
            r = int(start_color[0] + (end_color[0] - start_color[0]) * y / self.HEIGHT)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * y / self.HEIGHT)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * y / self.HEIGHT)
            draw.line([(0, y), (self.WIDTH, y)], fill=(r, g, b))

        # Draw stylish, semi-transparent overlapping geometric shapes
        shape_color = self.colors['primary_accent']
        draw.polygon([(0, 0), (self.WIDTH, 0), (self.WIDTH, 180), (0, 250)], fill=ImageColor.getrgb(shape_color) + (50,))
        draw.polygon([(0, 0), (self.WIDTH, 0), (self.WIDTH, 140), (0, 210)], fill=ImageColor.getrgb(self.colors['primary']) + (70,))
        draw.polygon([(0, self.HEIGHT), (self.WIDTH, self.HEIGHT), (self.WIDTH, self.HEIGHT - 180), (0, self.HEIGHT - 250)], fill=ImageColor.getrgb(shape_color) + (50,))
        draw.polygon([(0, self.HEIGHT), (self.WIDTH, self.HEIGHT), (self.WIDTH, self.HEIGHT - 140), (0, self.HEIGHT - 210)], fill=ImageColor.getrgb(self.colors['primary']) + (70,))

        return img, draw

    def _draw_header(self, draw: ImageDraw.ImageDraw, base_img: Image.Image) -> int:
        """Draws the header with logo and institution name."""
        y_cursor = 40
        if self.logo_path and os.path.exists(self.logo_path):
            with Image.open(self.logo_path).convert("RGBA") as logo:
                logo.thumbnail((100, 100), Image.LANCZOS)
                logo_x = (self.WIDTH - logo.width) // 2
                base_img.paste(logo, (logo_x, y_cursor), logo)
                y_cursor += logo.height + 15
        else:
            y_cursor += 30

        institution_name = getattr(self.staff.institution, 'name', 'INSTITUTE NAME').upper()
        draw.text((self.WIDTH / 2, y_cursor), institution_name, font=self.fonts['org_name'], fill=self.colors['text_light'], anchor='mt')
        y_cursor += 40
        draw.text((self.WIDTH / 2, y_cursor), "FACULTY IDENTITY CARD", font=self.fonts['title'], fill=self.colors['text_muted'], anchor='mt')
        
        return y_cursor + 45 # Return next position

    def _draw_photo(self, draw: ImageDraw.ImageDraw, base_img: Image.Image, y_pos: int) -> int:
        """Draws the faculty photo inside a styled circular frame."""
        size = 180
        x = (self.WIDTH - size) // 2
        
        # Create a decorative border
        draw.ellipse((x - 6, y_pos - 6, x + size + 6, y_pos + size + 6), fill=self.colors['primary_accent'])
        draw.ellipse((x - 3, y_pos - 3, x + size + 3, y_pos + size + 3), fill=self.colors['text_light'])

        photo_path = getattr(self.staff.photo, 'path', None)
        if photo_path and os.path.exists(photo_path):
            with Image.open(photo_path).convert("RGBA") as photo_img:
                photo_img = photo_img.resize((size, size), Image.LANCZOS)
                # Create a circular mask for the photo
                mask = Image.new('L', (size, size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
                base_img.paste(photo_img, (x, y_pos), mask)
        else:
            # Placeholder if no photo is available
            draw.ellipse((x, y_pos, x + size, y_pos + size), fill=self.colors['text_muted'])
            draw.text((x + size / 2, y_pos + size / 2), "NO PHOTO", font=self.fonts['department'], fill=self.colors['text_dark'], anchor='mm')
        
        return y_pos + size + 30

    def _draw_identity(self, draw: ImageDraw.ImageDraw, y_start: int) -> int:
        """Draws the faculty's name and department."""
        full_name = self.staff.user.get_full_name().upper()
        draw.text((self.WIDTH / 2, y_start), full_name, font=self.fonts['name'], fill=self.colors['text_light'], anchor='mt')
        
        y_cursor = y_start + 60
        
        department = getattr(self.staff, 'department', None)
        if department:
            department_text = str(department).upper()
            draw.text((self.WIDTH / 2, y_cursor), department_text, font=self.fonts['department'], fill=self.colors['secondary'], anchor='mt')
        
        return y_cursor + 55

    def _draw_details(self, draw: ImageDraw.ImageDraw, y_start: int):
        """Draws the detailed faculty information section."""
        details = [
            ('employee_id', 'Faculty ID', self.staff.employee_id),
            ('designation', 'Designation', self.staff.designation.name if self.staff.designation else 'N/A'),
            ('qualification', 'Qualification', self.faculty.get_qualification_display()),
            ('specialization', 'Specialization', self.faculty.get_specialization_display()),
            ('phone', 'Mobile', self.staff.personal_phone or 'N/A'),
        ]
        
        line_height = 48
        for i, (icon, label, value) in enumerate(details):
            self._draw_info_line(draw, y_start + i * line_height, icon, label, value)

    def _draw_info_line(self, draw, y, icon_key, label, value):
        """Helper to draw a single line of information."""
        icon = self.ICON_MAP.get(icon_key, '?')
        safe_value = force_str(value) if value else ""
        
        x_icon, x_label, x_value = 60, 100, 280
        
        draw.text((x_icon, y), icon, font=self.fonts['icon'], fill=self.colors['primary'], anchor='lm')
        draw.text((x_label, y), f"{label}:", font=self.fonts['details_label'], fill=self.colors['text_muted'], anchor='lm')
        draw.text((x_value, y), safe_value, font=self.fonts['details_value'], fill=self.colors['text_light'], anchor='lm')

    def _draw_footer(self, draw: ImageDraw.ImageDraw, base_img: Image.Image):
        """Draws the footer containing the QR code and signature area."""
        qr_size = 110
        y_bottom = self.HEIGHT - qr_size - self.MARGIN - 20

        # --- QR Code ---
        qr_data = (
            f"Name: {self.staff.user.get_full_name()}\n"
            f"ID: {self.staff.employee_id}\n"
            f"Designation: {self.staff.designation.name if self.staff.designation else 'N/A'}\n"
            f"Specialization: {self.faculty.get_specialization_display()}"
        )
        
        qr_img = qrcode.make(qr_data, box_size=4, border=2).convert('RGBA')
        
        # Recolor the QR code to match the theme
        qr_data_pixels = qr_img.getdata()
        new_qr_data = []
        qr_color = ImageColor.getrgb(self.colors['text_dark'])
        for item in qr_data_pixels:
            if item[0] < 128:  # If black
                new_qr_data.append(qr_color + (255,))
            else:  # If white
                new_qr_data.append((255, 255, 255, 0)) # Transparent background
        qr_img.putdata(new_qr_data)
        
        qr_img = qr_img.resize((qr_size, qr_size))
        
        # Draw a rounded background for the QR code
        qr_bg_x, qr_bg_y = self.MARGIN + 10, y_bottom
        draw.rounded_rectangle(
            (qr_bg_x, qr_bg_y, qr_bg_x + qr_size + 10, qr_bg_y + qr_size + 10),
            radius=8,
            fill=self.colors['text_light']
        )
        base_img.paste(qr_img, (qr_bg_x + 5, qr_bg_y + 5), qr_img)

        # --- Signature and Stamp ---
        sig_x_start = self.WIDTH - 250
        sig_x_end = self.WIDTH - self.MARGIN - 20
        sig_y = y_bottom + qr_size

        # Stamp
        stamp_y = sig_y - 110
        stamp_x = sig_x_start + 40
        if self.stamp_path and os.path.exists(self.stamp_path):
            with Image.open(self.stamp_path).convert("RGBA") as stamp_img:
                stamp_img.thumbnail((100, 100), Image.LANCZOS)
                base_img.paste(stamp_img, (stamp_x, stamp_y), stamp_img)
        else:
            draw.ellipse((stamp_x, stamp_y, stamp_x + 90, stamp_y + 90), outline=self.colors['secondary'], width=2)
            draw.text((stamp_x + 45, stamp_y + 45), "STAMP", font=self.fonts['department'], fill=self.colors['secondary'], anchor='mm')
            
        # Signature Line
        draw.line((sig_x_start, sig_y - 15, sig_x_end, sig_y - 15), fill=self.colors['primary'], width=2)
        draw.text((sig_x_start + (sig_x_end - sig_x_start) / 2, sig_y),
                  "Authorised Signatory", font=self.fonts['footer'],
                  fill=self.colors['text_light'], anchor='ms')


    def generate_id_card(self) -> BytesIO:
        """
        Orchestrates the drawing process and returns the final image as a byte buffer.
        """
        base_img, draw = self._create_canvas()

        y_cursor = self._draw_header(draw, base_img)
        y_cursor = self._draw_photo(draw, base_img, y_cursor)
        y_cursor = self._draw_identity(draw, y_cursor)
        
        self._draw_details(draw, y_cursor) 
        self._draw_footer(draw, base_img)

        # Save the image to an in-memory buffer
        img_buffer = BytesIO()
        base_img.save(img_buffer, format='PNG', dpi=(300, 300))
        img_buffer.seek(0)
        return img_buffer

    def get_id_card_response(self) -> HttpResponse:
        """Generates the ID card and returns it as a Django HttpResponse."""
        img_buffer = self.generate_id_card()
        response = HttpResponse(img_buffer.getvalue(), content_type='image/png')
        safe_employee_id = "".join(c for c in str(self.staff.employee_id) if c.isalnum())
        response['Content-Disposition'] = f'attachment; filename="faculty_{safe_employee_id}_id_card.png"'
        return response