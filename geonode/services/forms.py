#########################################################################
#
# Copyright (C) 2017 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

import logging

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import taggit

from . import enumerations
from .models import Service
from .serviceprocessors import get_service_handler
from geonode.services.serviceprocessors import get_available_service_types

logger = logging.getLogger(__name__)


class CreateServiceForm(forms.Form):

    url = forms.CharField(
        label=_("Service URL"),
        max_length=512,
        widget=forms.TextInput(
            attrs={"size": "65", "class": "inputText", "required": "", "type": "url", "autocomplete": "off"}
        ),
    )
    type = forms.ChoiceField(
        label=_("Service Type"),
        choices=[(k, v["label"]) for k, v in get_available_service_types().items()],  # from dictionary to tuple
        initial="AUTO",
    )

    username = forms.CharField(
        required=False,
        initial=None,
        label=_("Username (optional)"),
        max_length=200,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    password = forms.CharField(
        required=False,
        initial=None,
        label=_("password (optional)"),
        max_length=200,
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
    )

    def clean_url(self):
        proposed_url = self.cleaned_data["url"]
        existing = Service.objects.filter(base_url=proposed_url).exists()
        if existing:
            raise ValidationError(_("Service %(url)s is already registered"), params={"url": proposed_url})
        return proposed_url

    def clean(self):
        """Validates form fields that depend on each other"""
        super().clean()
        url = self.cleaned_data.get("url")
        service_type = self.cleaned_data.get("type")
        if url is not None and service_type is not None:
            try:
                service_handler = get_service_handler(
                    base_url=url,
                    service_type=service_type,
                    username=self.cleaned_data.get("username", None),
                    password=self.cleaned_data.get("password", None),
                )
            except Exception as e:
                logger.error(f"CreateServiceForm cleaning error: {e}")
                raise ValidationError(_("Could not connect to the service at %(url)s"), params={"url": url})
            if not service_handler.probe():
                raise ValidationError(_("Could not connect to the service at %(url)s"), params={"url": url})
            elif service_type not in (enumerations.AUTO, enumerations.OWS):
                if service_handler.service_type != service_type:
                    raise ValidationError(
                        _("Found service of type %(found_type)s instead " "of %(service_type)s"),
                        params={"found_type": service_handler.service_type, "service_type": service_type},
                    )
            self.cleaned_data["service_handler"] = service_handler
            self.cleaned_data["type"] = service_handler.service_type

    def clean_username(self):
        # the form return empty string, we want None if is not provided
        return self.cleaned_data["username"] or None

    def clean_password(self):
        # the form return empty string, we want None if is not provided
        return self.cleaned_data["password"] or None


class ServiceForm(forms.ModelForm):
    title = forms.CharField(
        label=_("Title"), max_length=255, widget=forms.TextInput(attrs={"size": "60", "class": "inputText"})
    )
    description = forms.CharField(label=_("Description"), widget=forms.Textarea(attrs={"cols": 60}))
    abstract = forms.CharField(label=_("Abstract"), widget=forms.Textarea(attrs={"cols": 60}))
    keywords = taggit.forms.TagField(required=False)

    class Meta:
        model = Service
        fields = (
            "title",
            "description",
            "abstract",
            "keywords",
        )
