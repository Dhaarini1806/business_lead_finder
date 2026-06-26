"""Forms for Forge OS extraction modules."""

from django import forms

INPUT = {"class": "input", "autocomplete": "off"}


class GoogleMapsForm(forms.Form):
    business_type = forms.CharField(
        max_length=160,
        widget=forms.TextInput({**INPUT, "placeholder": "Restaurants, Gym, Dental Clinic"}),
    )
    location = forms.CharField(
        max_length=255,
        widget=forms.TextInput({**INPUT, "placeholder": "Chennai, India"}),
    )
    radius_km = forms.FloatField(
        required=False, min_value=0.5, max_value=50,
        widget=forms.NumberInput({**INPUT, "placeholder": "8"}),
    )
    max_results = forms.IntegerField(
        required=False, min_value=1, max_value=2000,
        widget=forms.NumberInput({**INPUT, "placeholder": "200"}),
    )

    def clean_business_type(self):
        return self.cleaned_data["business_type"].strip()

    def clean_location(self):
        return self.cleaned_data["location"].strip()


class WebsiteScraperForm(forms.Form):
    url = forms.CharField(
        max_length=400,
        widget=forms.TextInput({**INPUT, "placeholder": "https://example.com"}),
    )
    crawl = forms.BooleanField(required=False)
    max_pages = forms.IntegerField(
        required=False, min_value=1, max_value=25,
        widget=forms.NumberInput({**INPUT, "placeholder": "5"}),
    )


class EmailFinderForm(forms.Form):
    person = forms.CharField(
        required=False, max_length=160,
        widget=forms.TextInput({**INPUT, "placeholder": "Jane Doe"}),
    )
    domain = forms.CharField(
        max_length=200,
        widget=forms.TextInput({**INPUT, "placeholder": "acme.com"}),
    )
    company = forms.CharField(
        required=False, max_length=200,
        widget=forms.TextInput({**INPUT, "placeholder": "Acme Inc (optional)"}),
    )
    verify = forms.BooleanField(required=False, initial=True)


class LinkedInForm(forms.Form):
    search_url = forms.CharField(
        required=False, max_length=600,
        widget=forms.TextInput({**INPUT, "placeholder": "LinkedIn / Sales Navigator search URL (optional)"}),
    )
    keyword = forms.CharField(
        required=False, max_length=160,
        widget=forms.TextInput({**INPUT, "placeholder": "VP Sales · SaaS"}),
    )
    pasted = forms.CharField(
        required=False,
        widget=forms.Textarea({
            "class": "input",
            "rows": 6,
            "placeholder": "Paste rows: Name, Position, Company, Industry, Company Size, LinkedIn URL",
        }),
    )
