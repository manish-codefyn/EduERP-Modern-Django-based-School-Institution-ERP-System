import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageColor
import qrcode
from django.conf import settings
from django.http import HttpResponse
from django.utils.encoding import force_str

# It's good practice to handle potential missing modules gracefully
try:
    from typing import Tuple
except ImportError:
    Tuple = None


class TeacherIDCardGenerator:
    """
    Generates an attractive and stylish ID card for a teacher.

    This class features a modern dark theme with geometric accents,
    refreshed icons, and a clean, professional layout. The public interface
    remains unchanged for seamless integration.
    """
    # --- Configuration Constants for Easy Styling ---

    # Card Dimensions
    WIDTH, HEIGHT = 600, 900
    MARGIN = 10

    # New stylish color palette (can be overridden by Django settings)
    DEFAULT_COLORS = {
        'background': '#2C3E50',  # Dark Slate Blue
        'primary': '#1ABC9C',     # Teal
        'secondary': '#F39C12',   # Gold/Orange
        'text_light': '#ECF0F1',  # Light Grey/Off-white
        'text_dark': '#2C3E50',   # Used for text on light backgrounds if any
        'text_muted': '#95A5A6',  # Muted Grey
    }

    # Refreshed Font Awesome 6 Solid Icons
    ICON_MAP = {
        'employee_id': '\uf2c1',  # ID Badge
        'designation': '\uf554',  # User Tie
        'phone': '\uf879',        # Mobile Alt
        'dob': '\uf1fd',          # Birthday Cake
        'email': '\uf1fa',        # Paper Plane
    }

    def __init__(self, teacher, logo_path=None, stamp_path=None):
        """
        Initializes the generator. The signature is unchanged.
        """
        self.teacher = teacher
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
        """Loads fonts, with a fallback. Unchanged logic."""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            font_dir = os.path.join(base_dir, "static", "fonts")
            self.fonts = {
                'org_name': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-ExtraBold.ttf"), 26),
                'title': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Regular.ttf"), 16),
                'name': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Bold.ttf"), 34),
                'department': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Medium.ttf"), 20),
                'details_label': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Regular.ttf"), 16),
                'details_value': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Medium.ttf"), 18),
                'footer': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Regular.ttf"), 16),
                'icon': ImageFont.truetype(os.path.join(font_dir, "Font Awesome 6 Free-Solid-900.ttf"), 20),
            }
        except (IOError, KeyError):
            default_font = ImageFont.load_default()
            font_keys = ['org_name', 'title', 'name', 'department', 'details_label', 'details_value', 'footer', 'icon']
            self.fonts = {key: default_font for key in font_keys}

    def _create_canvas(self) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
        """Creates the base image with a dark background and geometric shapes."""
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.colors['background'])
        draw = ImageDraw.Draw(img)

        # Draw stylish geometric shapes for header and footer
        # Header shape
        draw.polygon([(0, 0), (self.WIDTH, 0), (self.WIDTH, 220), (0, 150)], fill=self.colors['primary'])
        # Footer shape
        draw.polygon([(0, self.HEIGHT - 150), (self.WIDTH, self.HEIGHT - 220), (self.WIDTH, self.HEIGHT), (0, self.HEIGHT)], fill=self.colors['primary'])
        
        return img, draw

    def _draw_header(self, draw, base_img):
        """Draws the header with logo and institution name on the geometric shape."""
        y_cursor = 40
        if self.logo_path and os.path.exists(self.logo_path):
            logo = Image.open(self.logo_path).convert("RGBA")
            logo.thumbnail((100, 100), Image.LANCZOS)
            logo_x = (self.WIDTH - logo.width) // 2
            base_img.paste(logo, (logo_x, y_cursor), logo)
            y_cursor += logo.height + 15
        else:
            y_cursor += 30 # Placeholder space

        institution_name = getattr(self.teacher.institution, 'name', 'INSTITUTE').upper()
        draw.text((self.WIDTH / 2, y_cursor), institution_name, font=self.fonts['org_name'], fill=self.colors['text_light'], anchor='mm')
        y_cursor += 35
        draw.text((self.WIDTH / 2, y_cursor), "TEACHER IDENTITY CARD", font=self.fonts['title'], fill=self.colors['text_light'], anchor='mm')
        
        # Return Y position for the next element (photo)
        return y_cursor + 30  # Added gap after header

    def _draw_photo(self, draw, base_img, y_pos, extra_padding=30):
        """Draws the photo with a stylish circular border."""
        size = 180
        x = self.WIDTH // 2 - size // 2
        
        # Decorative borders
        draw.ellipse((x - 5, y_pos - 5, x + size + 5, y_pos + size + 5), fill=self.colors['primary'])
        draw.ellipse((x - 2, y_pos - 2, x + size + 2, y_pos + size + 2), fill=self.colors['background'])

        if self.teacher.photo and hasattr(self.teacher.photo, 'path') and os.path.exists(self.teacher.photo.path):
            photo_img = Image.open(self.teacher.photo.path).convert("RGBA").resize((size, size), Image.LANCZOS)
            mask = Image.new('L', (size, size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
            base_img.paste(photo_img, (x, y_pos), mask)
        else:
            draw.ellipse((x, y_pos, x + size, y_pos + size), fill=self.colors['text_muted'])
            draw.text((x + size / 2, y_pos + size / 2), "Photo", font=self.fonts['department'], fill=self.colors['text_light'], anchor='mm')
        
        # Return y position + size + padding
        return y_pos + size + extra_padding

    def _draw_identity(self, draw, y_start, extra_padding=40):
        """Draws the teacher's name and department."""
        full_name = " ".join(filter(None, [self.teacher.first_name, self.teacher.middle_name, self.teacher.last_name])).upper()
        draw.text((self.WIDTH / 2, y_start), full_name, font=self.fonts['name'], fill=self.colors['text_light'], anchor='mm')
        
        # Add gap between name and designation
        y_cursor = y_start + 50  # Increased gap between name and designation
        
        department = getattr(self.teacher, 'department', None)
        if department:
            draw.text((self.WIDTH / 2, y_cursor), str(department).upper(), font=self.fonts['department'], fill=self.colors['secondary'], anchor='mm')
        
        # Add gap after designation before details
        return y_cursor + 50  # Increased gap after designation

    def _draw_details(self, draw, y_start):
        """Draws the detailed information section."""
        details = [
            ('employee_id', 'Employee ID', self.teacher.employee_id),
            ('designation', 'Designation', self.teacher.get_designation_display()),
            ('phone', 'Mobile', self.teacher.mobile),
            ('dob', 'Date of Birth', self.teacher.dob.strftime('%d %b, %Y') if self.teacher.dob else 'N/A'),
            ('email', 'Email', self.teacher.email),
        ]
        line_height = 45  # Increased line height for better spacing
        for i, (icon, label, value) in enumerate(details):
            self._draw_info_line(draw, y_start + i * line_height, icon, label, value)

    def _draw_info_line(self, draw, y, icon_key, label, value):
        """Helper to draw a single line of information with new colors."""
        icon = self.ICON_MAP.get(icon_key, '?')
        safe_value = force_str(value) if value else ""
        x_icon, x_label, x_value = 80, 115, 260
        draw.text((x_icon, y), icon, font=self.fonts['icon'], fill=self.colors['primary'], anchor='lm')
        draw.text((x_label, y), f"{label}:", font=self.fonts['details_label'], fill=self.colors['text_muted'], anchor='lm')
        draw.text((x_value, y), safe_value, font=self.fonts['details_value'], fill=self.colors['text_light'], anchor='lm')

    def _draw_footer(self, draw, base_img):
        """Draws the QR code, stamp, and signature line."""
        y_bottom = self.HEIGHT - 170
        qr_size = 100
        full_name = f"{self.teacher.first_name} {self.teacher.last_name}"
        qr_data = f"ID: {self.teacher.employee_id}\nName: {full_name}\nDesignation: {self.teacher.get_designation_display()}"
        
        # Styled QR Code
        qr_img = qrcode.make(
            qr_data, box_size=4, border=2
        ).convert('RGBA')
        
        # Recolor QR to match theme
        qr_data = qr_img.getdata()
        new_qr_data = []
        for item in qr_data:
            if item[0] in list(range(200)): # Black pixels
                new_qr_data.append(tuple(int(c * 255) for c in ImageColor.getrgb(self.colors['primary'])))
            else: # White pixels
                new_qr_data.append((255, 255, 255, 0)) # Transparent
        qr_img.putdata(new_qr_data)
        
        qr_img = qr_img.resize((qr_size, qr_size))
        base_img.paste(qr_img, (self.MARGIN + 20, y_bottom), qr_img)

        # Authorized Signature
        sig_x_start, sig_x_end = self.WIDTH - 250, self.WIDTH - self.MARGIN - 20
        sig_y = y_bottom + qr_size
        draw.text((sig_x_start + (sig_x_end - sig_x_start) / 2, sig_y),
                  "Authorized Signature", font=self.fonts['footer'],
                  fill=self.colors['text_light'], anchor='ms')
        draw.line((sig_x_start, sig_y - 15, sig_x_end, sig_y - 15), fill=self.colors['primary'], width=2)

        # Stamp
        stamp_y = sig_y - 110
        stamp_x = sig_x_start + 40
        if self.stamp_path and os.path.exists(self.stamp_path):
            stamp_img = Image.open(self.stamp_path).convert("RGBA")
            stamp_img.thumbnail((100, 100), Image.LANCZOS)
            base_img.paste(stamp_img, (stamp_x, stamp_y), stamp_img)
        else:
            # Placeholder stamp
            draw.ellipse((stamp_x, stamp_y, stamp_x + 80, stamp_y + 80), outline=self.colors['secondary'], width=3)
            draw.text((stamp_x + 40, stamp_y + 40), "STAMP", font=self.fonts['department'],
                      fill=self.colors['secondary'], anchor='mm')

    def generate_id_card(self):
        """
        Orchestrates drawing with proper spacing between sections.
        """
        base_img, draw = self._create_canvas()

        # 1️⃣ Header
        y_cursor = self._draw_header(draw, base_img)

        # 2️⃣ Photo (with gap after header)
        y_cursor = self._draw_photo(draw, base_img, y_cursor, extra_padding=40)  # Increased gap after photo

        # 3️⃣ Name & Department (with gap after photo)
        y_cursor = self._draw_identity(draw, y_cursor, extra_padding=40)  # Increased gap after identity

        # 4️⃣ Details section (with gap after identity)
        self._draw_details(draw, y_cursor + 20)  # Added gap before details start

        # 5️⃣ Footer
        self._draw_footer(draw, base_img)

        # Save image
        img_buffer = BytesIO()
        base_img.save(img_buffer, format='PNG', dpi=(300, 300))
        img_buffer.seek(0)
        return img_buffer

    def get_id_card_response(self):
        """Generates the ID card and returns a Django HttpResponse. Unchanged logic."""
        img_buffer = self.generate_id_card()
        response = HttpResponse(img_buffer.getvalue(), content_type='image/png')
        safe_employee_id = "".join(c for c in str(self.teacher.employee_id) if c.isalnum())
        response['Content-Disposition'] = f'attachment; filename="{safe_employee_id}_id_card.png"'
        return response