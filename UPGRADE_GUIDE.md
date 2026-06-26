# FORGE.OS Upgrade Guide — CRM Features & Performance Enhancements

This guide walks you through integrating the new CRM features, email templates, and website analyzer into your existing FORGE.OS installation.

---

## 📋 What's New

### 1. **Lead Status Tracking** ✓
- Track lead status: New → Contacted → Qualified → Converted
- Last contacted timestamp
- Notes field for each lead
- Activity timeline showing all interactions

### 2. **Email Templates System** ✓
- Pre-built templates:
  - Cold outreach for website services
  - IT services pitch
  - Website audit & SEO optimization
  - Follow-up emails
- Template customization with lead data
- Email composer with preview
- Copy-to-clipboard functionality

### 3. **Website Analyzer** ✓
- SSL/HTTPS certificate validation
- SEO score (0-100) with checklist
- Page load time measurement
- Mobile responsiveness detection
- Actionable recommendations
- Analysis history tracking

### 4. **CRM Dashboard** ✓
- Lead status breakdown
- Recent activity timeline
- Today's contacts count
- Website analysis summary
- Quick lead actions

### 5. **Performance Optimizations** ✓
- Lazy loading for large datasets
- Database indexes for fast queries
- Caching support
- Keyboard shortcuts (coming soon)

### 6. **Dark/Light Theme** ✓
- Theme toggle in top-right corner
- Smooth transitions
- Persistent theme preference

---

## 🚀 Installation Steps

### Step 1: Copy New Files

Copy these files to your project:

```bash
# Services
cp leads/services/website_analyzer.py leads/services/
cp leads/services/email_templates.py leads/services/

# Models (reference - merge manually)
cp leads/models_enhanced.py leads/

# Views (merge with existing views.py)
cp leads/views_crm.py leads/

# Templates
cp templates/leads/lead_detail.html templates/leads/
cp templates/leads/email_composer.html templates/leads/
cp templates/leads/website_analyzer.html templates/leads/

# Migration
cp leads/migrations/0002_add_crm_features.py leads/migrations/
```

### Step 2: Update Models

**Edit `leads/models.py` and add these fields to the `Business` model:**

```python
# Add these imports at the top
from django.db.models import TextChoices

# Add this class
class LeadStatusChoices(TextChoices):
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    QUALIFIED = "qualified", "Qualified"
    CONVERTED = "converted", "Converted"
    REJECTED = "rejected", "Rejected"

# In the Business model, add these fields:
class Business(models.Model):
    # ... existing fields ...
    
    # CRM Fields (add these)
    status = models.CharField(
        max_length=20,
        choices=LeadStatusChoices.choices,
        default=LeadStatusChoices.NEW,
        db_index=True
    )
    notes = models.TextField(blank=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    
    # Update Meta.indexes:
    class Meta:
        # ... existing meta ...
        indexes = [
            # ... existing indexes ...
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["-last_contacted_at"]),
        ]
```

**Add new models to `leads/models.py`:**

Copy the content from `models_enhanced.py` (the EmailTemplate, LeadActivity, and WebsiteAnalysis classes).

### Step 3: Register New Models in Admin

**Edit `leads/admin.py`:**

```python
from .models import EmailTemplate, LeadActivity, WebsiteAnalysis

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['template_type', 'subject', 'is_active', 'created_at']
    list_filter = ['is_active', 'template_type']
    search_fields = ['subject', 'body']

@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ['business', 'activity_type', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['business__name', 'description']
    readonly_fields = ['created_at']

@admin.register(WebsiteAnalysis)
class WebsiteAnalysisAdmin(admin.ModelAdmin):
    list_display = ['url', 'status', 'seo_score', 'last_checked_at']
    list_filter = ['status', 'last_checked_at']
    search_fields = ['url']
    readonly_fields = ['created_at', 'last_checked_at']
```

### Step 4: Update URLs

**Edit `leads/urls.py` and add these URL patterns:**

```python
from .views_crm import (
    lead_detail,
    update_lead_status,
    add_lead_note,
    email_composer,
    render_email_template,
    log_email_sent,
    website_analyzer,
    website_analysis_detail,
    bulk_update_status,
    bulk_export_emails,
    crm_dashboard,
)

urlpatterns = [
    # ... existing patterns ...
    
    # Lead Management
    path('leads/<int:lead_id>/', lead_detail, name='lead_detail'),
    path('leads/<int:lead_id>/status/', update_lead_status, name='update_lead_status'),
    path('leads/<int:lead_id>/note/', add_lead_note, name='add_lead_note'),
    
    # Email Composer
    path('email-composer/<int:lead_id>/', email_composer, name='email_composer'),
    path('email-template/<int:lead_id>/', render_email_template, name='render_email_template'),
    path('email-sent/<int:lead_id>/', log_email_sent, name='log_email_sent'),
    
    # Website Analyzer
    path('website-analyzer/', website_analyzer, name='website_analyzer'),
    path('website-analysis/<int:analysis_id>/', website_analysis_detail, name='website_analysis_detail'),
    
    # Bulk Actions
    path('bulk-status/', bulk_update_status, name='bulk_update_status'),
    path('bulk-emails/', bulk_export_emails, name='bulk_export_emails'),
    
    # CRM Dashboard
    path('crm-dashboard/', crm_dashboard, name='crm_dashboard'),
]
```

### Step 5: Install Dependencies

**Update `requirements.txt`:**

```bash
# Add if not already present
beautifulsoup4>=4.15.0
requests>=2.34.2
```

Run:
```bash
pip install -r requirements.txt
```

### Step 6: Run Migrations

```bash
python manage.py migrate leads
```

### Step 7: Populate Email Templates

Create a Django shell script to populate default templates:

```bash
python manage.py shell
```

```python
from leads.models import EmailTemplate

templates = [
    {
        "template_type": "cold_outreach",
        "subject": "Quick Website Review for {business_name}",
        "body": """Hi {contact_name},

I came across {business_name} and noticed some quick wins we could implement for your website.

I specialize in helping businesses like yours improve their online presence through:
- Website optimization & speed improvements
- SEO enhancements
- Mobile responsiveness
- Security & performance audits

Would you be open to a quick 15-minute call to discuss how we could help?

Best regards,
{sender_name}
{sender_email}
{sender_phone}""",
        "description": "General cold outreach for website services"
    },
    # ... add other templates from services/email_templates.py DEFAULT_TEMPLATES
]

for template in templates:
    EmailTemplate.objects.get_or_create(
        template_type=template["template_type"],
        defaults={
            "subject": template["subject"],
            "body": template["body"],
            "description": template["description"],
        }
    )

print("Templates created!")
```

### Step 8: Update Base Template

**Edit `templates/base.html` to add theme toggle:**

Add this to your navbar/header:

```html
<!-- Theme Toggle (add to top-right of navbar) -->
<div class="theme-toggle">
    <button id="theme-toggle-btn" class="theme-btn" title="Toggle dark mode">
        🌙
    </button>
</div>

<style>
.theme-toggle {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
}

.theme-btn {
    background: #f0f0f0;
    border: 1px solid #ddd;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    cursor: pointer;
    font-size: 20px;
    transition: all 0.3s;
}

.theme-btn:hover {
    background: #e0e0e0;
}

body.dark-mode {
    background: #1a1a1a;
    color: #e0e0e0;
}

body.dark-mode .theme-btn {
    background: #333;
    border-color: #555;
}
</style>

<script>
// Theme toggle
const themeBtn = document.getElementById('theme-toggle-btn');
const savedTheme = localStorage.getItem('theme') || 'light';

if (savedTheme === 'dark') {
    document.body.classList.add('dark-mode');
    themeBtn.textContent = '☀️';
}

themeBtn.addEventListener('click', () => {
    const isDark = document.body.classList.toggle('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    themeBtn.textContent = isDark ? '☀️' : '🌙';
});
</script>
```

---

## 🔧 Configuration

### Website Analyzer Settings

**In `config/settings.py`:**

```python
# Website Analyzer
WEBSITE_ANALYZER_TIMEOUT = 10  # seconds
WEBSITE_ANALYZER_USER_AGENT = "FORGE.OS Website Analyzer / 1.0"
```

### Email Template Variables

Available variables for templates:
- `{business_name}` — Lead business name
- `{contact_name}` — Contact person name
- `{sender_name}` — Your name
- `{sender_email}` — Your email
- `{sender_phone}` — Your phone number

---

## 📊 Usage Examples

### 1. View Lead Details

```
Navigate to: /leads/<lead_id>/
```

Features:
- View all lead information
- Change status with dropdown
- Add notes
- See activity timeline
- Quick action buttons (call, email, analyze website)

### 2. Compose Email

```
Navigate to: /email-composer/<lead_id>/
```

Steps:
1. Select template or customize
2. Fill in recipient and sender info
3. Preview email
4. Copy to clipboard or mark as sent

### 3. Analyze Website

```
Navigate to: /website-analyzer/
```

Steps:
1. Enter website URL
2. Wait for analysis
3. View results and recommendations
4. Export or share report

### 4. Bulk Actions

From any leads table:
1. Select multiple leads
2. Choose bulk action (update status, export emails)
3. Execute

---

## 🎨 Customization

### Add Custom Email Template

In Django admin:
1. Go to Email Templates
2. Click "Add Email Template"
3. Fill in template type, subject, body
4. Save

Or programmatically:

```python
from leads.models import EmailTemplate

EmailTemplate.objects.create(
    template_type="custom",
    subject="Your subject here",
    body="Your body here",
    description="Your description",
    is_active=True
)
```

### Customize Website Analyzer

Edit `leads/services/website_analyzer.py`:
- Adjust timeout: `WEBSITE_ANALYZER_TIMEOUT`
- Add more SEO checks in `_check_seo()`
- Modify recommendations in `_generate_recommendations()`

---

## 🚀 Performance Tips

### 1. Database Optimization

```bash
# Create indexes
python manage.py migrate

# Check query performance
python manage.py shell
>>> from django.db import connection
>>> from django.test.utils import CaptureQueriesContext
>>> with CaptureQueriesContext(connection) as ctx:
>>>     # Run your query
>>>     pass
>>> print(f"Queries: {len(ctx)}")
```

### 2. Caching

Enable Redis caching in `config/settings.py`:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### 3. Lazy Loading

Templates already use lazy loading via HTMX. For custom views:

```python
from django.core.paginator import Paginator

def my_view(request):
    items = Business.objects.all()
    paginator = Paginator(items, 50)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'template.html', {'page_obj': page_obj})
```

---

## 🐛 Troubleshooting

### Migration Errors

```bash
# Reset migrations (dev only!)
python manage.py migrate leads zero
python manage.py migrate leads

# Or create new migration
python manage.py makemigrations
python manage.py migrate
```

### Website Analyzer Timeout

If analyzer times out:
1. Increase timeout in settings: `WEBSITE_ANALYZER_TIMEOUT = 15`
2. Check network connectivity
3. Verify URL is accessible

### Email Template Not Found

```python
from leads.services.email_templates import EmailTemplateManager

manager = EmailTemplateManager()
print(manager.list_templates())  # See available templates
```

---

## 📈 Next Steps

1. **Test thoroughly** — Run all tests: `python manage.py test leads`
2. **Customize templates** — Add your company branding
3. **Train users** — Show team how to use new features
4. **Monitor performance** — Check slow queries
5. **Gather feedback** — Iterate based on user feedback

---

## 📞 Support

For issues or questions:
1. Check Django logs: `python manage.py runserver --debug`
2. Review this guide
3. Check Django documentation
4. Consult OpenStreetMap API docs for extraction issues

---

**Happy lead hunting! 🎯**
