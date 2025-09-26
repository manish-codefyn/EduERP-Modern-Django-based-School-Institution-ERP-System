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


class StaffIDCardGenerator:
    """
    Generates an attractive and stylish ID card for a staff member.

    This class features a professional design with a gradient background,
    dynamic geometric shapes, and a refined color palette for a premium feel.
    """
    # --- Configuration Constants for Easy Styling ---

    # Card Dimensions
    WIDTH, HEIGHT = 600, 900
    MARGIN = 10

    # New professional and stylish color palette
    DEFAULT_COLORS = {
        'background_start': '#1D2B3E', # Deep Navy Blue
        'background_end': '#2C3E50',   # Dark Slate Blue (from original for a subtle gradient)
        'primary': '#48CAE4',         # Bright Cyan
        'primary_accent': '#00B4D8',  # Slightly Darker Cyan for depth
        'secondary': '#FFD166',       # Warm Gold/Saffron
        'text_light': '#FFFFFF',      # Pure White for crisp text
        'text_dark': '#1D2B3E',       # Dark Navy for text on light backgrounds
        'text_muted': '#CAF0F8',      # Very Light Cyan/Muted Blue
    }

    # Refreshed Font Awesome 6 Solid Icons (No changes needed here)
    ICON_MAP = {
        'employee_id': '\uf2c1',
        'designation': '\uf554',
        'phone': '\uf879',
        'dob': '\uf1fd',
        'email': '\uf1fa',
        'department': '\uf0c0',
        'staff_type': '\uf509',
    }

    def __init__(self, staff, logo_path=None, stamp_path=None):
        """
        Initializes the generator for a staff member.
        """
        self.staff = staff
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
        """Loads fonts, with a fallback."""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            font_dir = os.path.join(base_dir, "static", "fonts")
            self.fonts = {
                'org_name': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-ExtraBold.ttf"), 26),
                'title': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Regular.ttf"), 16),
                # --- MODIFIED FONT SIZES AND WEIGHTS ---
                'name': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Bold.ttf"), 38), # Increased size
                'department': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Bold.ttf"), 24), # Made Bold and increased size
                'details_label': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Bold.ttf"), 20), # Made Bold, increased size
                'details_value': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Bold.ttf"), 22), # Made Bold, increased size
                'footer': ImageFont.truetype(os.path.join(font_dir, "poppins", "Poppins-Regular.ttf"), 16),
                'icon': ImageFont.truetype(os.path.join(font_dir, "Font Awesome 6 Free-Solid-900.ttf"), 24), # Increased icon size
            }
        except (IOError, KeyError):
            default_font = ImageFont.load_default()
            font_keys = ['org_name', 'title', 'name', 'department', 'details_label', 'details_value', 'footer', 'icon']
            self.fonts = {key: default_font for key in font_keys}

    def _create_canvas(self) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
        """Creates the base image with a gradient background and dynamic shapes."""
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT))
        draw = ImageDraw.Draw(img)

        # Create a smooth vertical gradient for the background
        start_color = ImageColor.getrgb(self.colors['background_start'])
        end_color = ImageColor.getrgb(self.colors['background_end'])
        for y in range(self.HEIGHT):
            r = int(start_color[0] + (end_color[0] - start_color[0]) * y / self.HEIGHT)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * y / self.HEIGHT)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * y / self.HEIGHT)
            draw.line([(0, y), (self.WIDTH, y)], fill=(r, g, b))

        # Draw stylish overlapping geometric shapes for a modern look
        draw.polygon([(0, 0), (self.WIDTH, 0), (self.WIDTH, 180), (0, 250)], fill=self.colors['primary_accent'])
        draw.polygon([(0, 0), (self.WIDTH, 0), (self.WIDTH, 140), (0, 210)], fill=self.colors['primary'])
        draw.polygon([(0, self.HEIGHT), (self.WIDTH, self.HEIGHT), (self.WIDTH, self.HEIGHT - 180), (0, self.HEIGHT - 250)], fill=self.colors['primary_accent'])
        draw.polygon([(0, self.HEIGHT), (self.WIDTH, self.HEIGHT), (self.WIDTH, self.HEIGHT - 140), (0, self.HEIGHT - 210)], fill=self.colors['primary'])

        return img, draw

    def _draw_header(self, draw, base_img):
        """Draws the header with logo and institution name."""
        y_cursor = 40
        if self.logo_path and os.path.exists(self.logo_path):
            logo = Image.open(self.logo_path).convert("RGBA")
            logo.thumbnail((100, 100), Image.LANCZOS)
            logo_x = (self.WIDTH - logo.width) // 2
            base_img.paste(logo, (logo_x, y_cursor), logo)
            y_cursor += logo.height + 15
        else:
            y_cursor += 30

        institution_name = getattr(self.staff.institution, 'name', 'INSTITUTE').upper()
        draw.text((self.WIDTH / 2, y_cursor), institution_name, font=self.fonts['org_name'], fill=self.colors['text_light'], anchor='mm')
        y_cursor += 35
        draw.text((self.WIDTH / 2, y_cursor), "STAFF IDENTITY CARD", font=self.fonts['title'], fill=self.colors['text_muted'], anchor='mm')
        
        return y_cursor + 40 # Increased gap

    def _draw_photo(self, draw, base_img, y_pos, extra_padding=30):
        """Draws the photo with a stylish circular border."""
        size = 180
        x = self.WIDTH // 2 - size // 2
        
        draw.ellipse((x - 6, y_pos - 6, x + size + 6, y_pos + size + 6), fill=self.colors['primary_accent'])
        draw.ellipse((x - 4, y_pos - 4, x + size + 4, y_pos + size + 4), fill=self.colors['text_light'])

        if self.staff.photo and hasattr(self.staff.photo, 'path') and os.path.exists(self.staff.photo.path):
            photo_img = Image.open(self.staff.photo.path).convert("RGBA").resize((size, size), Image.LANCZOS)
            mask = Image.new('L', (size, size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
            base_img.paste(photo_img, (x, y_pos), mask)
        else:
            draw.ellipse((x, y_pos, x + size, y_pos + size), fill=self.colors['text_muted'])
            draw.text((x + size / 2, y_pos + size / 2), "Photo", font=self.fonts['department'], fill=self.colors['text_dark'], anchor='mm')
        
        return y_pos + size + extra_padding

    def _draw_identity(self, draw, y_start, extra_padding=40):
        """Draws the staff's name and department."""
        full_name = self.staff.user.get_full_name().upper()
        draw.text((self.WIDTH / 2, y_start), full_name, font=self.fonts['name'], fill=self.colors['text_light'], anchor='mm')
        
        y_cursor = y_start + 50 # Adjusted spacing for larger name font
        
        department = getattr(self.staff, 'department', None)
        if department:
            department_text = str(department).upper()
            draw.text((self.WIDTH / 2, y_cursor), department_text, font=self.fonts['department'], fill=self.colors['secondary'], anchor='mm')
        
        return y_cursor + 45

    def _draw_details(self, draw, y_start):
        """Draws the detailed information section."""
        details = [
            ('employee_id', 'Employee ID', self.staff.employee_id),
            ('designation', 'Designation', self.staff.designation.name if self.staff.designation else 'N/A'),
            ('department', 'Department', self.staff.department.name if self.staff.department else 'N/A'),
            ('staff_type', 'Staff Type', self.staff.get_staff_type_display()),
            ('phone', 'Mobile', self.staff.personal_phone if self.staff.personal_phone else 'N/A'),
            ('email', 'Email', self.staff.personal_email if self.staff.personal_email else 'N/A'),
        ]
        line_height = 55  # --- MODIFIED: Increased line height for bigger fonts
        for i, (icon, label, value) in enumerate(details):
            self._draw_info_line(draw, y_start + i * line_height, icon, label, value)

    def _draw_info_line(self, draw, y, icon_key, label, value):
        """Helper to draw a single line of information with the new color scheme."""
        icon = self.ICON_MAP.get(icon_key, '?')
        safe_value = force_str(value) if value else ""
        
        # --- MODIFIED: Adjusted X coordinates for new font sizes
        x_icon, x_label, x_value = 60, 100, 280
        
        draw.text((x_icon, y), icon, font=self.fonts['icon'], fill=self.colors['primary'], anchor='lm')
        draw.text((x_label, y), f"{label}:", font=self.fonts['details_label'], fill=self.colors['text_muted'], anchor='lm')
        draw.text((x_value, y), safe_value, font=self.fonts['details_value'], fill=self.colors['text_light'], anchor='lm')

    def _draw_footer(self, draw, base_img):
        """Draws the QR code, stamp, and signature line."""
        y_bottom = self.HEIGHT - 170
        qr_size = 100
        full_name = self.staff.user.get_full_name()
        qr_data = f"ID: {self.staff.employee_id}\nName: {full_name}\nDesignation: {self.staff.designation.name if self.staff.designation else 'N/A'}\nDepartment: {self.staff.department.name if self.staff.department else 'N/A'}"
        
        qr_img = qrcode.make(qr_data, box_size=4, border=2).convert('RGBA')
        
        qr_data_pixels = qr_img.getdata()
        new_qr_data = []
        qr_color = ImageColor.getrgb(self.colors['text_dark'])
        for item in qr_data_pixels:
            if item[0] < 128:
                new_qr_data.append(qr_color + (255,))
            else:
                new_qr_data.append((255, 255, 255, 0))
        qr_img.putdata(new_qr_data)
        
        qr_img = qr_img.resize((qr_size, qr_size))
        
        qr_bg_x, qr_bg_y = self.MARGIN + 15, y_bottom - 5
        draw.rounded_rectangle(
            (qr_bg_x, qr_bg_y, qr_bg_x + qr_size + 10, qr_bg_y + qr_size + 10),
            radius=10,
            fill=self.colors['text_muted']
        )
        base_img.paste(qr_img, (qr_bg_x + 5, qr_bg_y + 5), qr_img)

        sig_x_start, sig_x_end = self.WIDTH - 250, self.WIDTH - self.MARGIN - 20
        sig_y = y_bottom + qr_size
        draw.text((sig_x_start + (sig_x_end - sig_x_start) / 2, sig_y),
                  "Authorized Signature", font=self.fonts['footer'],
                  fill=self.colors['text_light'], anchor='ms')
        draw.line((sig_x_start, sig_y - 15, sig_x_end, sig_y - 15), fill=self.colors['primary'], width=2)

        stamp_y = sig_y - 110
        stamp_x = sig_x_start + 40
        if self.stamp_path and os.path.exists(self.stamp_path):
            stamp_img = Image.open(self.stamp_path).convert("RGBA")
            stamp_img.thumbnail((100, 100), Image.LANCZOS)
            base_img.paste(stamp_img, (stamp_x, stamp_y), stamp_img)
        else:
            draw.ellipse((stamp_x, stamp_y, stamp_x + 80, stamp_y + 80), outline=self.colors['secondary'], width=3)
            draw.text((stamp_x + 40, stamp_y + 40), "STAMP", font=self.fonts['department'],
                      fill=self.colors['secondary'], anchor='mm')

    def generate_id_card(self):
        """
        Orchestrates the drawing of all ID card components.
        """
        base_img, draw = self._create_canvas()

        y_cursor = self._draw_header(draw, base_img)
        y_cursor = self._draw_photo(draw, base_img, y_cursor, extra_padding=35)
        y_cursor = self._draw_identity(draw, y_cursor, extra_padding=35)
        
        # Add a small gap before the details section starts
        self._draw_details(draw, y_cursor + 10) 
        
        self._draw_footer(draw, base_img)

        img_buffer = BytesIO()
        base_img.save(img_buffer, format='PNG', dpi=(300, 300))
        img_buffer.seek(0)
        return img_buffer

    def get_id_card_response(self):
        """Generates the ID card and returns a Django HttpResponse."""
        img_buffer = self.generate_id_card()
        response = HttpResponse(img_buffer.getvalue(), content_type='image/png')
        safe_employee_id = "".join(c for c in str(self.staff.employee_id) if c.isalnum())
        response['Content-Disposition'] = f'attachment; filename="{safe_employee_id}_staff_id_card.png"'
        return response