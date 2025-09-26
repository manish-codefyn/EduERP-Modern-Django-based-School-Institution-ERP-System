from django import forms
from .models import Notice, Broadcast, NotificationTemplate,PushNotification
from django.utils import timezone
import json
# Add to existing forms.py
from .models import NoticeAudience


class NoticeAudienceFilterForm(forms.Form):
    notice = forms.ModelChoiceField(
        queryset=Notice.objects.none(),
        required=False,
        empty_label="All Notices"
    )
    read_status = forms.ChoiceField(
        choices=[('', 'All Status'), ('read', 'Read'), ('unread', 'Unread')],
        required=False
    )
    delivery_status = forms.ChoiceField(
        choices=[('', 'All Status'), ('delivered', 'Delivered'), ('undelivered', 'Not Delivered')],
        required=False
    )
    search = forms.CharField(required=False, max_length=100)

    def __init__(self, *args, **kwargs):
        institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        if institution:
            self.fields['notice'].queryset = Notice.objects.filter(
                institution=institution, 
                is_published=True
            ).order_by('-publish_date')


class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = [
            'title', 'content', 'priority', 'audience', 'is_published',
            'publish_date', 'expiry_date', 'attachment'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'audience': forms.Select(attrs={'class': 'form-select'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'publish_date': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
            'expiry_date': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_publish_date(self):
        publish_date = self.cleaned_data.get('publish_date')
        if publish_date and publish_date < timezone.now():
            raise forms.ValidationError("Publish date cannot be in the past.")
        return publish_date
    
    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        publish_date = self.cleaned_data.get('publish_date')
        
        if expiry_date and publish_date and expiry_date <= publish_date:
            raise forms.ValidationError("Expiry date must be after publish date.")
        return expiry_date

class BroadcastForm(forms.ModelForm):
    class Meta:
        model = Broadcast
        fields = [
            'name', 'audience', 'channel', 'message', 'template', 'scheduled_for'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'audience': forms.Select(attrs={'class': 'form-select'}),
            'channel': forms.Select(attrs={'class': 'form-select'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'template': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_for': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
        }

class VariableField(forms.JSONField):
    def prepare_value(self, value):
        if isinstance(value, dict):
            return json.dumps(value, indent=2)
        return value

class VariableField(forms.JSONField):
    def prepare_value(self, value):
        if isinstance(value, dict):
            return json.dumps(value, indent=2)
        return value

class NotificationTemplateForm(forms.ModelForm):
    variables = VariableField(
        widget=forms.Textarea(attrs={
            'placeholder': '{\n  "user_name": "Full name of the user",\n  "amount": "Transaction amount",\n  "date": "Transaction date"\n}',
            'rows': 6,
            'class': 'json-field'
        }),
        help_text="Enter variables as JSON key-value pairs. Key: variable name, Value: description"
    )
    
    class Meta:
        model = NotificationTemplate
        exclude = ['institution']
        fields = '__all__'
    
    def clean_variables(self):
        variables = self.cleaned_data['variables']
        try:
            if isinstance(variables, str):
                variables = json.loads(variables)
            return variables
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format")
        

class PushNotificationForm(forms.ModelForm):
    class Meta:
        model = PushNotification
        fields = [
            'title', 'message', 'priority', 'audience', 
            'data', 'template', 'template_variables', 'scheduled_for', 'status'
        ]
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
            'data': forms.Textarea(attrs={'rows': 2}),
            'template_variables': forms.Textarea(attrs={'rows': 2}),
            'scheduled_for': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }