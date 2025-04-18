from django import forms


class CoreTempForm(forms.Form):
    site_id = forms.CharField()
    mgmt_subnet = forms.CharField()


class IntDescriptionForm(forms.Form):
    site_id = forms.CharField()
    mgmt_subnet = forms.GenericIPAddressField()


class IosUpgradeForm(forms.Form):
    site_id = forms.CharField()


class PaloForm(forms.Form):
    firewall_ip = forms.GenericIPAddressField(label="Firewall IP")
    wan_ip = forms.CharField(max_length=30)


class PaloOsUpgradeForm(forms.Form):
    firewall_ip = forms.CharField(label="Enter each IP to be upgraded", widget=forms.Textarea)
    version = forms.CharField(max_length=20, label="Code Version")