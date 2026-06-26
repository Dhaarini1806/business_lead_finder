"""
Email Template Service — Pre-built templates for outreach campaigns.

Provides:
- Cold outreach for website services
- IT services pitch
- Website audit/SEO optimization offer
- Follow-up emails
- Template customization
"""

from typing import Dict, List


DEFAULT_TEMPLATES = {
    "cold_outreach": {
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
    
    "it_services": {
        "subject": "IT Infrastructure Review for {business_name}",
        "body": """Hi {contact_name},

I help businesses optimize their IT infrastructure and reduce operational costs.

For {business_name}, I see potential improvements in:
- Cloud infrastructure optimization
- Security & compliance
- System automation
- Cost reduction (typically 20-30% savings)

Would you like to discuss how we could help streamline your IT operations?

Let's schedule a brief call at your convenience.

Best regards,
{sender_name}
{sender_email}
{sender_phone}""",
        "description": "IT services pitch for technical decision makers"
    },
    
    "website_audit": {
        "subject": "Free Website Audit for {business_name}",
        "body": """Hi {contact_name},

I'm offering a complimentary website audit for select businesses in your area.

Our audit covers:
✓ SEO performance & opportunities
✓ Page speed & performance metrics
✓ Mobile responsiveness
✓ Security & SSL status
✓ Conversion optimization
✓ Competitor benchmarking

I'll send you a detailed report with actionable recommendations.

Interested? Reply with your preferred time for a quick call.

Best regards,
{sender_name}
{sender_email}
{sender_phone}""",
        "description": "Website audit and SEO optimization offer"
    },
    
    "follow_up": {
        "subject": "Following up: {business_name} Website Opportunity",
        "body": """Hi {contact_name},

I wanted to follow up on my previous message about optimizing {business_name}'s online presence.

I understand you might be busy, but this could be a quick win for your business:
- Improved search rankings
- Better user experience
- Increased conversions
- Enhanced security

Would this week work for a brief conversation?

Looking forward to connecting.

Best regards,
{sender_name}
{sender_email}
{sender_phone}""",
        "description": "Follow-up email after initial outreach"
    },
}


class EmailTemplateManager:
    """Manage email templates and customization."""
    
    @staticmethod
    def get_template(template_type: str) -> Dict | None:
        """Get a template by type."""
        return DEFAULT_TEMPLATES.get(template_type)
    
    @staticmethod
    def list_templates() -> List[Dict]:
        """List all available templates."""
        templates = []
        for template_type, content in DEFAULT_TEMPLATES.items():
            templates.append({
                "type": template_type,
                "subject": content["subject"],
                "description": content["description"]
            })
        return templates
    
    @staticmethod
    def render_template(
        template_type: str,
        variables: Dict[str, str]
    ) -> Dict | None:
        """Render a template with variables."""
        template = DEFAULT_TEMPLATES.get(template_type)
        if not template:
            return None
        
        # Set defaults for missing variables
        defaults = {
            "contact_name": "there",
            "business_name": "your business",
            "sender_name": "Your Name",
            "sender_email": "your@email.com",
            "sender_phone": "+1-XXX-XXX-XXXX",
        }
        
        # Merge provided variables with defaults
        all_vars = {**defaults, **variables}
        
        # Render subject and body
        subject = template["subject"].format(**all_vars)
        body = template["body"].format(**all_vars)
        
        return {
            "type": template_type,
            "subject": subject,
            "body": body,
            "description": template["description"]
        }
    
    @staticmethod
    def customize_template(
        template_type: str,
        custom_subject: str = None,
        custom_body: str = None
    ) -> Dict | None:
        """Create a custom template based on existing one."""
        template = DEFAULT_TEMPLATES.get(template_type)
        if not template:
            return None
        
        return {
            "type": "custom",
            "subject": custom_subject or template["subject"],
            "body": custom_body or template["body"],
            "description": f"Custom version of {template_type}"
        }
    
    @staticmethod
    def extract_variables(template_text: str) -> List[str]:
        """Extract variable names from template text."""
        import re
        pattern = r'\{(\w+)\}'
        return list(set(re.findall(pattern, template_text)))


def get_template_for_business(business_data: Dict) -> Dict:
    """Suggest and render appropriate template based on business data."""
    manager = EmailTemplateManager()
    
    # Determine best template based on business category
    category = business_data.get("category", "").lower()
    
    if any(x in category for x in ["it", "tech", "software", "consulting"]):
        template_type = "it_services"
    elif any(x in category for x in ["retail", "restaurant", "shop", "store"]):
        template_type = "cold_outreach"
    else:
        template_type = "website_audit"
    
    # Render with business data
    variables = {
        "business_name": business_data.get("name", "your business"),
        "contact_name": business_data.get("contact_name", "there"),
    }
    
    return manager.render_template(template_type, variables)


def create_email_campaign_preview(
    template_type: str,
    businesses: List[Dict],
    sender_info: Dict
) -> List[Dict]:
    """Create preview emails for a campaign."""
    manager = EmailTemplateManager()
    previews = []
    
    for business in businesses:
        variables = {
            "business_name": business.get("name", "your business"),
            "contact_name": business.get("contact_name", "there"),
            "sender_name": sender_info.get("name", "Your Name"),
            "sender_email": sender_info.get("email", "your@email.com"),
            "sender_phone": sender_info.get("phone", "+1-XXX-XXX-XXXX"),
        }
        
        rendered = manager.render_template(template_type, variables)
        if rendered:
            rendered["business_id"] = business.get("id")
            rendered["business_name"] = business.get("name")
            previews.append(rendered)
    
    return previews
