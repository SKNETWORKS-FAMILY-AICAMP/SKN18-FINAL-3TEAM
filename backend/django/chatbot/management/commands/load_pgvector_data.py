"""
Django management command to load CSV data into PostgreSQL pgvector
"""
from django.core.management.base import BaseCommand
from backend.db_pipeline.postgres.ETL.load_to_pgvector import run


class Command(BaseCommand):
    help = 'Load CSV data into PostgreSQL pgvector database for LangGraph'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data load process...'))

        try:
            run()
            self.stdout.write(self.style.SUCCESS('Data load completed successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Data load failed: {str(e)}'))
            raise
