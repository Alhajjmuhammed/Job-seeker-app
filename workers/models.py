from django.db import models
from accounts.models import User


class Category(models.Model):
    """Job categories for workers"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Bootstrap icon class")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Skill(models.Model):
    """Skills related to categories"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    
    class Meta:
        ordering = ['name']
        unique_together = ['category', 'name']
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"


class WorkerProfile(models.Model):
    """Extended profile for workers"""
    
    AVAILABILITY_CHOICES = (
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('offline', 'Offline'),
    )
    
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='worker_profile')
    bio = models.TextField(blank=True, help_text="Brief introduction about yourself")
    profile_image = models.ImageField(upload_to='worker_profiles/', blank=True, null=True, help_text="Profile photo")
    
    # Location
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Sudan')
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Personal details
    RELIGION_CHOICES = (
        ('', 'Prefer not to say'),
        ('islam', 'Islam'),
        ('christianity', 'Christianity'),
        ('judaism', 'Judaism'),
        ('hinduism', 'Hinduism'),
        ('buddhism', 'Buddhism'),
        ('sikhism', 'Sikhism'),
        ('other', 'Other'),
    )
    
    religion = models.CharField(max_length=50, choices=RELIGION_CHOICES, blank=True, default='')
    can_work_everywhere = models.BooleanField(default=False, help_text="Available to work in any location")
    
    # Work details
    categories = models.ManyToManyField(Category, related_name='workers')
    skills = models.ManyToManyField(Skill, related_name='workers', blank=True)
    experience_years = models.IntegerField(default=0)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Status
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    is_featured = models.BooleanField(default=False)
    
    # Statistics
    total_jobs = models.IntegerField(default=0)
    completed_jobs = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Worker Profile"
    
    @property
    def completion_rate(self):
        if self.total_jobs > 0:
            return round((self.completed_jobs / self.total_jobs) * 100, 2)
        return 0
    
    @property
    def profile_completion(self):
        """Calculate profile completion percentage"""
        total_fields = 0
        completed_fields = 0
        
        # Check basic profile fields
        fields_to_check = [
            self.bio,
            self.address,
            self.city,
            self.state,
            self.country,
            self.postal_code,
        ]
        
        for field in fields_to_check:
            total_fields += 1
            if field and str(field).strip():
                completed_fields += 1
        
        # Check profile image
        total_fields += 1
        if self.profile_image:
            completed_fields += 1
        
        # Check categories (at least one)
        total_fields += 1
        if self.categories.exists():
            completed_fields += 1
        
        # Check experience years
        total_fields += 1
        if self.experience_years > 0:
            completed_fields += 1
        
        # Check hourly rate
        total_fields += 1
        if self.hourly_rate:
            completed_fields += 1
        
        # Check if has at least one document
        total_fields += 1
        if self.documents.exists():
            completed_fields += 1
        
        # Check if has at least one experience
        total_fields += 1
        if self.experiences.exists():
            completed_fields += 1
        
        # Check if has at least one custom skill
        total_fields += 1
        if self.custom_skills.exists():
            completed_fields += 1
        
        # Calculate percentage
        if total_fields > 0:
            return round((completed_fields / total_fields) * 100)
        return 0


class WorkerDocument(models.Model):
    """Documents uploaded by workers"""
    
    DOCUMENT_TYPES = (
        ('id', 'ID Card'),
        ('cv', 'CV/Resume'),
        ('certificate', 'Certificate'),
        ('license', 'License'),
        ('other', 'Other'),
    )
    
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='worker_documents/')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    rejection_reason = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.worker.user.username} - {self.get_document_type_display()}"


class WorkExperience(models.Model):
    """Work experience for workers"""
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='experiences')
    job_title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.worker.user.username} - {self.job_title} at {self.company}"
    
    @property
    def duration(self):
        """Calculate the duration of work experience"""
        from datetime import date
        
        end = self.end_date if self.end_date else date.today()
        
        # Calculate total months
        months_diff = (end.year - self.start_date.year) * 12 + (end.month - self.start_date.month)
        
        years = months_diff // 12
        months = months_diff % 12
        
        if years > 0 and months > 0:
            return f"{years} year{'s' if years > 1 else ''}, {months} month{'s' if months > 1 else ''}"
        elif years > 0:
            return f"{years} year{'s' if years > 1 else ''}"
        elif months > 0:
            return f"{months} month{'s' if months > 1 else ''}"
        else:
            return "Less than a month"


class CustomSkillRequest(models.Model):
    """Workers can request custom skills/categories not in the system"""
    
    REQUEST_TYPES = (
        ('category', 'Category'),
        ('skill', 'Skill'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='custom_requests')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    name = models.CharField(max_length=200, help_text="Name of the requested category or skill")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, 
                                 help_text="For skill requests, which category does it belong to?")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Admin feedback")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['worker', 'request_type', 'name', 'category']
    
    def __str__(self):
        return f"{self.worker.user.username} - {self.get_request_type_display()}: {self.name}"


class WorkerCustomSkill(models.Model):
    """Custom skills added by workers with optional certificates"""
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='custom_skills')
    name = models.CharField(max_length=200, help_text="Skill name")
    description = models.TextField(blank=True, help_text="Brief description of this skill")
    certificate = models.FileField(upload_to='skill_certificates/', null=True, blank=True, 
                                   help_text="Upload certificate (optional)")
    years_of_experience = models.IntegerField(default=0, help_text="Years of experience with this skill")
    is_verified = models.BooleanField(default=False, help_text="Admin verified this skill")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['worker', 'name']
    
    def __str__(self):
        return f"{self.worker.user.username} - {self.name}"


class WorkerCustomCategory(models.Model):
    """Custom categories added by workers"""
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='custom_categories')
    name = models.CharField(max_length=200, help_text="Category name")
    description = models.TextField(blank=True, help_text="What services do you offer in this category?")
    is_verified = models.BooleanField(default=False, help_text="Admin verified this category")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['worker', 'name']
    
    def __str__(self):
        return f"{self.worker.user.username} - {self.name}"
