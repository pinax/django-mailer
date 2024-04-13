from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from mailer.engine import send_all
from mailer.models import DontSendEntry, Message, MessageLog


def show_to(message):
    if message.email:
        return ", ".join(message.to_addresses)
    else:
        return "<Message data unavailable>"


show_to.short_description = "To"  # noqa: E305


def show_subject(message):
    if message.email:
        return message.subject
    else:
        return "<Message data unavailable>"


show_subject.short_description = "Subject"  # noqa: E305


class MessageAdminMixin:
    def plain_text_body(self, instance):
        email = instance.email
        if hasattr(email, "body"):
            return email.body
        else:
            return "<Can't decode>"


class MessageAdmin(MessageAdminMixin, admin.ModelAdmin):

    list_display = ["id", show_to, "subject", "when_added", "priority", "retry_count"]
    readonly_fields = ["plain_text_body"]
    date_hierarchy = "when_added"
    actions = ["send_messages"]

    def send_messages(self, request, queryset):
        send_all(queryset)
        messages.add_message(request, messages.INFO, _("Message(s) sent."))


class DontSendEntryAdmin(admin.ModelAdmin):

    list_display = ["to_address", "when_added"]


class MessageLogAdmin(MessageAdminMixin, admin.ModelAdmin):

    list_display = ["id", show_to, show_subject, "message_id", "when_attempted", "result"]
    list_filter = ["result"]
    date_hierarchy = "when_attempted"
    readonly_fields = ["plain_text_body", "message_id"]
    search_fields = ["message_id"]


admin.site.register(Message, MessageAdmin)
admin.site.register(DontSendEntry, DontSendEntryAdmin)
admin.site.register(MessageLog, MessageLogAdmin)
