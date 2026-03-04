# Generated migration for cancellation and rating fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0014_servicerequest_daily_rate_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicerequest',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, help_text='When request was cancelled', null=True),
        ),
        migrations.AddField(
            model_name='servicerequest',
            name='cancellation_reason',
            field=models.TextField(blank=True, help_text='Reason for cancellation'),
        ),
        migrations.AddField(
            model_name='servicerequest',
            name='client_rating',
            field=models.PositiveSmallIntegerField(blank=True, help_text="Client's rating of worker (1-5 stars)", null=True),
        ),
        migrations.AddField(
            model_name='servicerequest',
            name='client_review',
            field=models.TextField(blank=True, help_text="Client's review of the service"),
        ),
    ]
