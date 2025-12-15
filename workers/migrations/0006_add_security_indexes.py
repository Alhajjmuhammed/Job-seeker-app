# Generated manually for security and performance improvements
# Run with: python manage.py migrate

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workers', '0005_workerprofile_can_work_everywhere_and_more'),
    ]

    operations = [
        # Add database indexes for frequently filtered fields
        migrations.AlterField(
            model_name='workerprofile',
            name='verification_status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('verified', 'Verified'), ('rejected', 'Rejected')],
                default='pending',
                max_length=20,
                db_index=True  # Add index for fast filtering
            ),
        ),
        migrations.AlterField(
            model_name='workerprofile',
            name='availability',
            field=models.CharField(
                choices=[('available', 'Available'), ('busy', 'Busy'), ('offline', 'Offline')],
                default='available',
                max_length=20,
                db_index=True  # Add index for fast filtering
            ),
        ),
        migrations.AlterField(
            model_name='workerdocument',
            name='verification_status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
                default='pending',
                max_length=20,
                db_index=True  # Add index for admin queries
            ),
        ),
    ]
