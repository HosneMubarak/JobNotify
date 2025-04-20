from django import forms
from .models import Channels
from .utils import send_welcome_message


class ChannelsAdminForm(forms.ModelForm):
    class Meta:
        model = Channels
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make the user field more user-friendly
        self.fields['user'].required = False  # User will be auto-set if not provided

    def clean(self):
        cleaned_data = super().clean()

        # Only validate new channels (not updates) that have a config
        if not self.instance.pk and cleaned_data.get('config'):
            # Try to send welcome message
            config = cleaned_data.get('config')
            name = cleaned_data.get('name')

            if config and name:
                notification_sent = send_welcome_message(config, name)

                # If notification fails, raise validation error
                if not notification_sent:
                    self.add_error('config',
                                   "Channel configuration is invalid. Could not send welcome message. Please check the configuration URL.")

        return cleaned_data
