"""
Django management command to load CSV data into Neo4j
"""
from django.core.management.base import BaseCommand
from backend.db_pipeline.neo4j.ETL.load_to_neo4j import run_all


class Command(BaseCommand):
    help = 'Load CSV data into Neo4j graph database for LangGraph'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Neo4j data load process...'))

        try:
            run_all()
            self.stdout.write(self.style.SUCCESS('Neo4j data load completed successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Neo4j data load failed: {str(e)}'))
            raise
