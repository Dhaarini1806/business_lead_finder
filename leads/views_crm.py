"""
CRM Views for Forge OS — Lead management, email templates, website analysis.

New views:
- Lead detail page with activity timeline
- Email composer with template selection
- Website analyzer
- Lead status management
- Bulk actions
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.utils import timezone

from .models import Business, LeadActivity, WebsiteAnalysis
from .services.email_templates import EmailTemplateManager, get_template_for_business
from .services.website_analyzer import analyze_website


# ======================================================================= #
# Lead Detail & Management
# ======================================================================= #

@require_http_methods(["GET"])
def lead_detail(request, lead_id):
    """Display detailed lead information with activity timeline."""
    lead = get_object_or_404(Business, pk=lead_id)
    
    # Get activity timeline
    activities = lead.activities.all()[:20]
    
    # Get website analysis if available
    website_analysis = getattr(lead, 'website_analysis', None)
    
    # Get enrichment if available
    enrichment = getattr(lead, 'enrichment', None)
    
    context = {
        "lead": lead,
        "activities": activities,
        "website_analysis": website_analysis,
        "enrichment": enrichment,
        "status_choices": Business._meta.get_field("status").choices,
    }
    
    return render(request, "leads/lead_detail.html", context)


@require_http_methods(["POST"])
def update_lead_status(request, lead_id):
    """Update lead status via AJAX."""
    lead = get_object_or_404(Business, pk=lead_id)
    new_status = request.POST.get("status")
    
    if new_status in dict(Business._meta.get_field("status").choices):
        old_status = lead.status
        lead.status = new_status
        lead.last_contacted_at = timezone.now()
        lead.save()
        
        # Log activity
        LeadActivity.objects.create(
            business=lead,
            activity_type="status_changed",
            description=f"Status changed from {old_status} to {new_status}",
            metadata={"old_status": old_status, "new_status": new_status}
        )
        
        return JsonResponse({"success": True, "status": new_status})
    
    return JsonResponse({"success": False, "error": "Invalid status"}, status=400)


@require_http_methods(["POST"])
def add_lead_note(request, lead_id):
    """Add a note to a lead."""
    lead = get_object_or_404(Business, pk=lead_id)
    note = request.POST.get("note", "").strip()
    
    if note:
        lead.notes = (lead.notes or "") + f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {note}"
        lead.save()
        
        # Log activity
        LeadActivity.objects.create(
            business=lead,
            activity_type="note_added",
            description=note
        )
        
        return JsonResponse({"success": True})
    
    return JsonResponse({"success": False, "error": "Note cannot be empty"}, status=400)


# ======================================================================= #
# Email Composer
# ======================================================================= #

@require_http_methods(["GET"])
def email_composer(request, lead_id):
    """Email composer with template selection."""
    lead = get_object_or_404(Business, pk=lead_id)
    manager = EmailTemplateManager()
    
    # Get available templates
    templates = manager.list_templates()
    
    # Get suggested template for this business
    suggested = get_template_for_business({
        "name": lead.name,
        "category": lead.category,
    })
    
    context = {
        "lead": lead,
        "templates": templates,
        "suggested_template": suggested,
    }
    
    return render(request, "leads/email_composer.html", context)


@require_http_methods(["POST"])
def render_email_template(request, lead_id):
    """Render email template with lead data."""
    lead = get_object_or_404(Business, pk=lead_id)
    template_type = request.POST.get("template_type")
    
    manager = EmailTemplateManager()
    
    variables = {
        "business_name": lead.name,
        "contact_name": request.POST.get("contact_name", "there"),
        "sender_name": request.user.get_full_name() or request.user.username,
        "sender_email": request.user.email,
        "sender_phone": request.POST.get("sender_phone", ""),
    }
    
    rendered = manager.render_template(template_type, variables)
    
    if rendered:
        return JsonResponse({
            "success": True,
            "subject": rendered["subject"],
            "body": rendered["body"],
        })
    
    return JsonResponse({"success": False, "error": "Template not found"}, status=400)


@require_http_methods(["POST"])
def log_email_sent(request, lead_id):
    """Log that an email was sent to a lead."""
    lead = get_object_or_404(Business, pk=lead_id)
    
    template_type = request.POST.get("template_type")
    subject = request.POST.get("subject", "")
    
    lead.last_contacted_at = timezone.now()
    lead.save()
    
    # Log activity
    LeadActivity.objects.create(
        business=lead,
        activity_type="email_sent",
        description=f"Email sent: {subject}",
        metadata={"template": template_type, "subject": subject}
    )
    
    return JsonResponse({"success": True})


# ======================================================================= #
# Website Analyzer
# ======================================================================= #

@require_http_methods(["GET", "POST"])
def website_analyzer(request):
    """Website analyzer page."""
    if request.method == "POST":
        url = request.POST.get("url", "").strip()
        
        if not url:
            return JsonResponse({"success": False, "error": "URL required"}, status=400)
        
        # Ensure URL has protocol
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        # Run analysis
        results = analyze_website(url)
        
        # Try to find associated lead
        lead = Business.objects.filter(website=url).first()
        
        # Save analysis
        if lead:
            analysis, created = WebsiteAnalysis.objects.update_or_create(
                business=lead,
                defaults={
                    "url": url,
                    "has_ssl": results.get("has_ssl", False),
                    "ssl_valid": results.get("ssl_valid", False),
                    "seo_score": results.get("seo_score", 0),
                    "has_meta_description": results.get("has_meta_description", False),
                    "has_h1_tag": results.get("has_h1_tag", False),
                    "has_sitemap": results.get("has_sitemap", False),
                    "page_load_time_ms": results.get("page_load_time_ms"),
                    "is_mobile_responsive": results.get("is_mobile_responsive", False),
                    "recommendations": results.get("recommendations", []),
                    "status": results.get("status", "error"),
                }
            )
            
            # Log activity
            LeadActivity.objects.create(
                business=lead,
                activity_type="website_analyzed",
                description=f"Website analyzed: {results.get('status')}",
                metadata=results
            )
        else:
            # Create standalone analysis
            analysis = WebsiteAnalysis.objects.create(
                url=url,
                has_ssl=results.get("has_ssl", False),
                ssl_valid=results.get("ssl_valid", False),
                seo_score=results.get("seo_score", 0),
                has_meta_description=results.get("has_meta_description", False),
                has_h1_tag=results.get("has_h1_tag", False),
                has_sitemap=results.get("has_sitemap", False),
                page_load_time_ms=results.get("page_load_time_ms"),
                is_mobile_responsive=results.get("is_mobile_responsive", False),
                recommendations=results.get("recommendations", []),
                status=results.get("status", "error"),
            )
        
        return JsonResponse({
            "success": True,
            "analysis": {
                "id": analysis.id,
                "url": analysis.url,
                "has_ssl": analysis.has_ssl,
                "ssl_valid": analysis.ssl_valid,
                "seo_score": analysis.seo_score,
                "has_meta_description": analysis.has_meta_description,
                "has_h1_tag": analysis.has_h1_tag,
                "has_sitemap": analysis.has_sitemap,
                "page_load_time_ms": analysis.page_load_time_ms,
                "is_mobile_responsive": analysis.is_mobile_responsive,
                "recommendations": analysis.recommendations,
                "status": analysis.status,
            }
        })
    
    # GET request - show analyzer page
    recent_analyses = WebsiteAnalysis.objects.all().order_by("-last_checked_at")[:10]
    
    context = {
        "recent_analyses": recent_analyses,
    }
    
    return render(request, "leads/website_analyzer.html", context)


@require_http_methods(["GET"])
def website_analysis_detail(request, analysis_id):
    """Display detailed website analysis results."""
    analysis = get_object_or_404(WebsiteAnalysis, pk=analysis_id)
    
    context = {
        "analysis": analysis,
        "lead": analysis.business if analysis.business else None,
    }
    
    return render(request, "leads/website_analysis_detail.html", context)


# ======================================================================= #
# Bulk Actions
# ======================================================================= #

@require_http_methods(["POST"])
def bulk_update_status(request):
    """Update status for multiple leads."""
    lead_ids = request.POST.getlist("lead_ids[]")
    new_status = request.POST.get("status")
    
    if not lead_ids or not new_status:
        return JsonResponse({"success": False, "error": "Missing parameters"}, status=400)
    
    # Validate status
    valid_statuses = dict(Business._meta.get_field("status").choices)
    if new_status not in valid_statuses:
        return JsonResponse({"success": False, "error": "Invalid status"}, status=400)
    
    # Update leads
    updated = Business.objects.filter(
        pk__in=lead_ids
    ).update(
        status=new_status,
        last_contacted_at=timezone.now()
    )
    
    return JsonResponse({
        "success": True,
        "updated_count": updated
    })


@require_http_methods(["POST"])
def bulk_export_emails(request):
    """Export email addresses for selected leads."""
    lead_ids = request.POST.getlist("lead_ids[]")
    
    if not lead_ids:
        return JsonResponse({"success": False, "error": "No leads selected"}, status=400)
    
    leads = Business.objects.filter(pk__in=lead_ids).values("name", "email", "phone")
    
    # Format as CSV
    csv_lines = ["Name,Email,Phone"]
    for lead in leads:
        csv_lines.append(
            f'"{lead["name"]}","{lead["email"]}","{lead["phone"]}"'
        )
    
    csv_content = "\n".join(csv_lines)
    
    return JsonResponse({
        "success": True,
        "csv": csv_content,
        "filename": "leads_emails.csv"
    })


# ======================================================================= #
# Dashboard Enhancements
# ======================================================================= #

@require_http_methods(["GET"])
def crm_dashboard(request):
    """Enhanced CRM dashboard with lead metrics."""
    from django.db.models import Count, Q
    
    today = timezone.localdate()
    
    # Lead status breakdown
    status_breakdown = Business.objects.values("status").annotate(count=Count("id"))
    
    # Recent activities
    recent_activities = LeadActivity.objects.select_related("business").all()[:15]
    
    # Leads contacted today
    today_contacted = Business.objects.filter(
        last_contacted_at__date=today
    ).count()
    
    # Website analysis summary
    analysis_stats = WebsiteAnalysis.objects.values("status").annotate(count=Count("id"))
    
    context = {
        "status_breakdown": status_breakdown,
        "recent_activities": recent_activities,
        "today_contacted": today_contacted,
        "analysis_stats": analysis_stats,
        "total_leads": Business.objects.count(),
    }
    
    return render(request, "leads/crm_dashboard.html", context)
