# Generated migration for CRM features

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0001_initial'),
    ]

    operations = [
        # Add fields to Business model
        migrations.AddField(
            model_name='business',
            name='status',
            field=models.CharField(
                choices=[
                    ('new', 'New'),
                    ('contacted', 'Contacted'),
                    ('qualified', 'Qualified'),
                    ('converted', 'Converted'),
                    ('rejected', 'Rejected')
                ],
                db_index=True,
                default='new',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='business',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='business',
            name='last_contacted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        
        # Create EmailTemplate model
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('template_type', models.CharField(
                    choices=[
                        ('cold_outreach', 'Cold Outreach - Website Services'),
                        ('it_services', 'IT Services Pitch'),
                        ('website_audit', 'Website Audit & SEO Optimization'),
                        ('follow_up', 'Follow-up Email'),
                        ('custom', 'Custom Template')
                    ],
                    db_index=True,
                    max_length=20,
                    unique=True
                )),
                ('subject', models.CharField(max_length=200)),
                ('body', models.TextField()),
                ('description', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Email Template',
                'verbose_name_plural': 'Email Templates',
            },
        ),
        
        # Create LeadActivity model
        migrations.CreateModel(
            name='LeadActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_type', models.CharField(
                    choices=[
                        ('email_sent', 'Email Sent'),
                        ('call_made', 'Call Made'),
                        ('note_added', 'Note Added'),
                        ('status_changed', 'Status Changed'),
                        ('website_analyzed', 'Website Analyzed'),
                        ('enriched', 'Lead Enriched'),
                    ],
                    max_length=20
                )),
                ('description', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='leads.business')),
            ],
            options={
                'verbose_name': 'Lead Activity',
                'verbose_name_plural': 'Lead Activities',
            },
        ),
        
        # Create WebsiteAnalysis model
        migrations.CreateModel(
            name='WebsiteAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(db_index=True, max_length=400)),
                ('has_ssl', models.BooleanField(default=False)),
                ('ssl_valid', models.BooleanField(default=False)),
                ('ssl_expires_at', models.DateTimeField(blank=True, null=True)),
                ('seo_score', models.PositiveIntegerField(default=0)),
                ('has_meta_description', models.BooleanField(default=False)),
                ('has_h1_tag', models.BooleanField(default=False)),
                ('has_sitemap', models.BooleanField(default=False)),
                ('page_load_time_ms', models.PositiveIntegerField(blank=True, null=True)),
                ('is_mobile_responsive', models.BooleanField(default=False)),
                ('recommendations', models.JSONField(blank=True, default=list)),
                ('last_checked_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('status', models.CharField(
                    choices=[
                        ('healthy', 'Healthy'),
                        ('warning', 'Warning'),
                        ('critical', 'Critical'),
                        ('error', 'Error'),
                    ],
                    default='warning',
                    max_length=20
                )),
                ('business', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='website_analysis', to='leads.business')),
            ],
            options={
                'verbose_name': 'Website Analysis',
                'verbose_name_plural': 'Website Analyses',
            },
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='business',
            index=models.Index(fields=['status', '-created_at'], name='leads_busi_status_idx'),
        ),
        migrations.AddIndex(
            model_name='business',
            index=models.Index(fields=['-last_contacted_at'], name='leads_busi_contacted_idx'),
        ),
        migrations.AddIndex(
            model_name='leadactivity',
            index=models.Index(fields=['business', '-created_at'], name='leads_acti_business_idx'),
        ),
        migrations.AddIndex(
            model_name='leadactivity',
            index=models.Index(fields=['activity_type', '-created_at'], name='leads_acti_type_idx'),
        ),
        migrations.AddIndex(
            model_name='websiteanalysis',
            index=models.Index(fields=['url'], name='leads_web_url_idx'),
        ),
        migrations.AddIndex(
            model_name='websiteanalysis',
            index=models.Index(fields=['-last_checked_at'], name='leads_web_checked_idx'),
        ),
    ]
