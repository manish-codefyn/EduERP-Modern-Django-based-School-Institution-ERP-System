# utils.py
import re
from django.template import Template, Context
from django.utils.safestring import mark_safe


class TemplateRenderer:
    """Utility class for template rendering and variable management"""
    
    @staticmethod
    def render_template(content, variables):
        """Render template with variables using Django template syntax"""
        try:
            from django.template import Template, Context
            from django.utils.safestring import mark_safe
            
            template = Template(content)
            context = Context(variables)
            return mark_safe(template.render(context))
        except Exception as e:
            return f"Template rendering error: {str(e)}"
    
    @staticmethod
    def extract_variables(content):
        """Extract variables from template content (supports {{variable}} syntax)"""
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, content)
        variables = set()
        for match in matches:
            var = match.strip()
            if var:
                variables.add(var)
        return sorted(list(variables))
    
    @staticmethod
    def validate_variables(content, provided_variables):
        """Validate if all required variables are provided"""
        required_variables = TemplateRenderer.extract_variables(content)
        missing_variables = [var for var in required_variables if var not in provided_variables]
        return missing_variables

