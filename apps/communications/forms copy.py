from django import forms
from .models import Notice, Broadcast, NotificationTemplate
from django.utils import timezone

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

class NotificationTemplateForm(forms.ModelForm):
    variables = VariableField(
        widget=forms.Textarea(attrs={
            'placeholder': '{\n  "user_name": "Full name of the user",\n  "amount": "Transaction amount",\n  "date": "Transaction date"\n}',
            'rows': 6,
            'class': 'json-field'
        }),
        help_text="Enter variables as JSON key-value pairs. Key: variable name, Value: description"
    )
    


class NotificationTemplateForm(forms.ModelForm):
    class Meta:
        model = NotificationTemplate
        fields = [
            'name', 'template_type', 'subject', 'content', 'variables', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'template_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'variables': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Enter variables as JSON: {"variable1": "description1", "variable2": "description2"}'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

        class Meta:
        model = NotificationTemplate
        fields = '__all__'
    
    def clean_variables(self):
        variables = self.cleaned_data['variables']
        try:
            if isinstance(variables, str):
                variables = json.loads(variables)
            return variables
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format")