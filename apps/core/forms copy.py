
from django import forms
from django.utils.translation import gettext_lazy as _


class BaseForm(forms.ModelForm):
    """
    Base form class with common styling
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply common styling to all fields
        for field_name, field in self.fields.items():
            if isinstance(field, forms.CharField):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field, forms.EmailField):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field, forms.DateField):
                field.widget.attrs.update({'class': 'form-control datepicker'})
            elif isinstance(field, forms.ChoiceField):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field, forms.BooleanField):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field, forms.ModelChoiceField):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field, forms.ModelMultipleChoiceField):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field, forms.IntegerField):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field, forms.DecimalField):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field, forms.FileField):
                field.widget.attrs.update({'class': 'form-control'})
