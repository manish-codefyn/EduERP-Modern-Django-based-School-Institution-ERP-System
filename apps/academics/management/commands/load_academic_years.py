import json
import os
from django.core.management.base import BaseCommand
from academics.models import AcademicYear
from organization.models import Institution

class Command(BaseCommand):
    help = 'Load academic years from JSON file'
    
    def handle(self, *args, **options):
        file_path = os.path.join('apps', 'academics', 'data', 'academic_years.json')
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
            for item in data:
                try:
                    institution = Institution.objects.get(id=item['institution'])
                    
                    AcademicYear.objects.update_or_create(
                        id=item['id'],
                        defaults={
                            'institution': institution,
                            'name': item['name'],
                            'start_date': item['start_date'],
                            'end_date': item['end_date'],
                            'is_current': item.get('is_current', False)
                        }
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully loaded academic year: {item["name"]}')
                    )
                    
                except Institution.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Institution {item["institution"]} not found for academic year {item["name"]}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading academic year {item["name"]}: {str(e)}')
                    )
                    
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING('Academic years JSON file not found')
            )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully loaded academic years data')
        )