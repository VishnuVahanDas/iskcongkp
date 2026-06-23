# Generated migration for NityaSevaMandate model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0003_instacollect_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='NityaSevaMandate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=200)),
                ('mobile', models.CharField(max_length=10)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('seva_type', models.CharField(max_length=100)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('wants_80g', models.BooleanField(default=False)),
                ('pan_number', models.CharField(blank=True, max_length=10)),
                ('address_line1', models.CharField(blank=True, max_length=255)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('pincode', models.CharField(blank=True, max_length=6)),
                ('txnid', models.CharField(max_length=100, unique=True)),
                ('access_key', models.CharField(blank=True, max_length=500)),
                ('mandate_status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('active', 'Active'),
                        ('failed', 'Failed'),
                        ('cancelled', 'Cancelled'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('mandate_start', models.DateField(blank=True, null=True)),
                ('mandate_end', models.DateField(blank=True, null=True)),
                ('last_notification_id', models.CharField(blank=True, max_length=200)),
                ('last_notification_number', models.CharField(blank=True, max_length=100)),
                ('last_debit_number', models.CharField(blank=True, max_length=100)),
                ('last_debit_status', models.CharField(
                    choices=[
                        ('not_initiated', 'Not Initiated'),
                        ('notified', 'Notified'),
                        ('in_process', 'In Process'),
                        ('success', 'Success'),
                        ('failed', 'Failed'),
                    ],
                    default='not_initiated',
                    max_length=20,
                )),
                ('last_debit_pg_txnid', models.CharField(blank=True, max_length=200)),
                ('last_debited_at', models.DateTimeField(blank=True, null=True)),
                ('total_debits_done', models.IntegerField(default=0)),
                ('mandate_webhook_payload', models.JSONField(blank=True, null=True)),
                ('debit_webhook_payload', models.JSONField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Nitya Seva UPI AutoPay Mandate',
                'ordering': ['-created_at'],
            },
        ),
    ]
