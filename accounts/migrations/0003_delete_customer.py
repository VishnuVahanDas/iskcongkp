from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_customer_phone"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Customer",
        ),
    ]

