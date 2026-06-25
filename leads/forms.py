"""Forms for the Business Lead Finder."""

from django import forms


class SearchForm(forms.Form):
    """Simple two-field search form: business type + location."""

    business_type = forms.CharField(
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "e.g. Bakery, Gym, Dental Clinic",
                "autocomplete": "off",
            }
        ),
    )
    location = forms.CharField(
        max_length=160,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "e.g. Chromepet, Chennai, Tambaram",
                "autocomplete": "off",
            }
        ),
    )

    def clean_business_type(self):
        return self.cleaned_data["business_type"].strip()

    def clean_location(self):
        return self.cleaned_data["location"].strip()
