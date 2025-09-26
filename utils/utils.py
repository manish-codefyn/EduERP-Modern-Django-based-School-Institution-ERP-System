

import io
import os
import re
import qrcode
import requests 
import tempfile
import base64
from pathlib import Path
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.utils import timezone
from django.conf import settings
from email.mime.image import MIMEImage
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
    
def download_temp_image(image_url):
    response = requests.get(image_url, stream=True)
    if response.status_code == 200:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        for chunk in response.iter_content(1024):
            temp_file.write(chunk)
        temp_file.close()
        return temp_file.name
    return None


def qr_generate(data, size=2, version=2, border=0):
    """
    Generate a QR code and save it as a temporary file.
    Returns the absolute path of the saved QR code image.
    """
    qr = qrcode.QRCode(version=version, box_size=size, border=border)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp_file.name)
    return temp_file.name


def fetch_resources(uri, rel):
    """
    Fetch resources for xhtml2pdf.
    Supports both local and remote media files.
    """
    if uri.startswith(settings.MEDIA_URL):  # Local media
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
        return path
    elif uri.startswith("http"):  # Remote media (e.g., Cloudinary)
        response = requests.get(uri, stream=True)
        if response.status_code == 200:
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            for chunk in response.iter_content(1024):
                temp_file.write(chunk)
            temp_file.close()
            return temp_file.name
    return None


def render_to_pdf(template_src, context_dict={}):
    """Utility function to render HTML to PDF using xhtml2pdf"""
    html = render_to_string(template_src, context_dict)
    result = io.BytesIO()

    # Important: pass fetch_resources so images load properly
    pdf = pisa.pisaDocument(
        io.BytesIO(html.encode("UTF-8")),
        result,
        link_callback=fetch_resources 
    )

    if not pdf.err:
        return result.getvalue()   # return bytes, not HttpResponse
    return None


def export_pdf_response(pdf_content, filename):
    """Create HTTP response for PDF download"""
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response



def generate_qr_code_base64(data, size=3, version=2, border=1):
    """
    Generate QR code and return as base64 string
    """
    if isinstance(data, dict):
        data_str = "\n".join([f"{k}: {v}" for k, v in data.items()])
    else:
        data_str = str(data)
    
    qr = qrcode.QRCode(
        version=version,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=size,
        border=border,
    )
    qr.add_data(data_str)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffered = io.BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{qr_base64}"
# def fetch_resources(uri, rel):
#        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
#        return path


def SendMailWithImg(subject, context, template_name, to_mail, from_mail, images=()):
    """Html Send Through Email"""
    context = context
    subject = subject
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(subject, text_content, from_mail, [to_mail])
    email.attach_alternative(html_content, "text/html")
    email.content_subtype = "html"  # set the primary content to be text/html
    email.mixed_subtype = (
        "related"  # it is an important part that ensures embedding of an image
    )

    with open(image_path, mode="rb") as f:
        image = MIMEImage(f.read())
        email.attach(image)
        image.add_header("Content-ID", f"<{image_name}>")

    return email.send(fail_silently=False)


def SendMailInHtml(subject, context, template_name, to_mail, from_mail):
    """Html Send Through Email"""
    context = context
    subject = subject
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(subject, text_content, from_mail, [to_mail])
    email.attach_alternative(html_content, "text/html")
    return email.send(fail_silently=False)


def SendPDFInMail(subject, template_name, content, from_mail, to_mail, pdf_file):
    # """Html Send Through Email"""
    # send_mail = EmailMessage(
    # subject, 'context',
    # from_mail ,
    # [to_mail]
    # )
    # send_mail.attach_file(str(pdf_file))
    # return send_mail.send()

    """Html,PDF Send Through Email"""
    context = content
    subject = subject
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(subject, text_content, from_mail, [to_mail])
    msg.attach_alternative(html_content, "text/html")
    msg.attach_file(pdf_file)
    return msg.send()