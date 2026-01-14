"""
Django management command to load TTL data into Apache Fuseki
"""
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from backend.langgraph_fuseki.ontology.scripts.load_ttl_to_fuseki import (
    check_fuseki_connection,
    check_dataset_exists,
    create_dataset,
    delete_all_data,
    upload_ttl_file,
    count_triples,
    get_file_size
)


class Command(BaseCommand):
    help = 'Load TTL data into Apache Fuseki for LangGraph'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fuseki-url',
            type=str,
            default='http://localhost:3030',
            help='Fuseki server URL'
        )
        parser.add_argument(
            '--dataset',
            type=str,
            default='korean-history',
            help='Dataset name'
        )

    def handle(self, *args, **options):
        fuseki_url = options['fuseki_url']
        dataset = options['dataset']
        fuseki_user = 'admin'
        fuseki_password = os.getenv('FUSEKI_PASSWORD') or os.getenv('FUSEKI_ADMIN_PASSWORD') or 'fuseki1234'
        auth = (fuseki_user, fuseki_password)

        # TTL file path
        script_dir = Path(__file__).parent.parent.parent.parent.parent
        ttl_file = script_dir / "langgraph_fuseki" / "ontology" / "instances" / "korean_history_normalized.ttl"

        if not ttl_file.exists():
            self.stdout.write(self.style.ERROR(f'TTL file not found: {ttl_file}'))
            raise FileNotFoundError(f'TTL file not found: {ttl_file}')

        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS('Starting Fuseki TTL upload process...'))
        self.stdout.write(f"Fuseki URL: {fuseki_url}")
        self.stdout.write(f"Dataset:    {dataset}")
        self.stdout.write(f"File:       {ttl_file}")
        self.stdout.write(f"File size:  {get_file_size(ttl_file)}")
        self.stdout.write("")

        try:
            # 1. Check Fuseki connection
            self.stdout.write("🔍 Checking Fuseki server connection...")
            if not check_fuseki_connection(fuseki_url):
                raise ConnectionError(f"Cannot connect to Fuseki server ({fuseki_url})")
            self.stdout.write(self.style.SUCCESS("✅ Fuseki server connection successful"))

            # 2. Check/create dataset
            self.stdout.write("🔍 Checking dataset...")
            if not check_dataset_exists(fuseki_url, dataset, auth):
                self.stdout.write(f"Dataset '{dataset}' not found. Creating...")
                if create_dataset(fuseki_url, dataset, auth):
                    self.stdout.write(self.style.SUCCESS("✅ Dataset created successfully"))
                else:
                    raise Exception("Failed to create dataset")
            else:
                self.stdout.write(self.style.SUCCESS("✅ Dataset exists"))

            # 3. Delete existing data
            self.stdout.write("🗑️  Deleting existing data...")
            if delete_all_data(fuseki_url, dataset, auth):
                self.stdout.write(self.style.SUCCESS("✅ Existing data deleted"))
            else:
                self.stdout.write(self.style.WARNING("⚠️  No existing data to delete"))

            # 4. Upload TTL file
            self.stdout.write("📤 Uploading TTL file...")
            status_code, error_text = upload_ttl_file(fuseki_url, dataset, ttl_file, auth)

            if status_code in [200, 204]:
                self.stdout.write(self.style.SUCCESS("✅ TTL upload completed"))
            else:
                raise Exception(f"Upload failed with status {status_code}: {error_text[:500]}")

            # 5. Verify upload
            self.stdout.write("✔️  Verifying upload...")
            triple_count = count_triples(fuseki_url, dataset, auth)
            if triple_count >= 0:
                self.stdout.write(self.style.SUCCESS(f"✅ Uploaded triples: {triple_count:,}"))
            else:
                self.stdout.write(self.style.WARNING("⚠️  Could not verify triple count"))

            self.stdout.write("")
            self.stdout.write("=" * 70)
            self.stdout.write(self.style.SUCCESS('🎉 Fuseki data load completed successfully!'))
            self.stdout.write("=" * 70)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Fuseki data load failed: {str(e)}'))
            raise
