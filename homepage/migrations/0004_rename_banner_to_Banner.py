from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("homepage", "0003_top_header"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="banner",
            new_name="Banner",
        ),
    ]
