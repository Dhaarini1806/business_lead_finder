"""
Django admin for Forge OS — Lead Intelligence.

Admins can view searches/leads, delete duplicates, and export records to Excel.
"""

from django.contrib import admin
from django.http import HttpResponse

from .models import Business, Enrichment, ExportLog, Search
from .services.exporter import build_workbook


@admin.register(Search)
class SearchAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "business_type", "location",
                    "total_results", "status", "duration_seconds", "created_at")
    list_filter = ("source", "status", "created_at")
    search_fields = ("business_type", "location", "display_name")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


class EnrichmentInline(admin.StackedInline):
    model = Enrichment
    extra = 0


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "category", "company", "phone",
                    "email", "email_status", "search")
    list_filter = ("source", "category", "email_status")
    search_fields = ("name", "category", "address", "phone", "website",
                     "email", "company", "industry")
    list_select_related = ("search",)
    inlines = (EnrichmentInline,)
    actions = ("delete_duplicates", "export_to_excel")

    @admin.action(description="Delete duplicate leads (same name + address)")
    def delete_duplicates(self, request, queryset):
        seen, to_delete = set(), []
        for biz in Business.objects.all().order_by("id"):
            key = (biz.name.strip().lower(), biz.address.strip().lower(),
                   biz.email.strip().lower())
            if key in seen:
                to_delete.append(biz.id)
            else:
                seen.add(key)
        deleted, _ = Business.objects.filter(id__in=to_delete).delete()
        self.message_user(request, f"Deleted {deleted} duplicate lead(s).")

    @admin.action(description="Export selected leads to Excel")
    def export_to_excel(self, request, queryset):
        src = queryset.first().source if queryset.exists() else None
        workbook = build_workbook(queryset, source=src)
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="leads.xlsx"'
        workbook.save(response)
        return response


@admin.register(Enrichment)
class EnrichmentAdmin(admin.ModelAdmin):
    list_display = ("business", "industry", "employee_count", "ai_score", "created_at")
    search_fields = ("business__name", "industry", "domain")
    list_filter = ("industry",)


@admin.register(ExportLog)
class ExportLogAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "fmt", "business_type", "location",
                    "record_count", "created_at")
    list_filter = ("source", "fmt", "created_at")
    search_fields = ("business_type", "location")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
