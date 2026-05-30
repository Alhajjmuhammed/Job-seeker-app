# Generated manually for security and performance improvements
# Run with: python manage.py migrate

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0004_auto_20251021_1146'),
    ]

    operations = [
        # Add database indexes for frequently filtered fields
        migrations.AlterField(
            model_name='jobrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('open', 'Open'),
                    ('in_progress', 'In Progress'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled')
                ],
                default='open',
                max_length=20,
                db_index=True  # Add index for fast job filtering
            ),
        ),
        migrations.AlterField(
            model_name='jobapplication',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('accepted', 'Accepted'),
                    ('rejected', 'Rejected'),
                    ('withdrawn', 'Withdrawn')
                ],
                default='pending',
                max_length=20,
                db_index=True  # Add index for application queries
            ),
        ),
        migrations.AlterField(
            model_name='message',
            name='is_read',
            field=models.BooleanField(
                default=False,
                db_index=True  # Add index for unread message queries
            ),
        ),
    ]
