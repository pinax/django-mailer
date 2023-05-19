from __future__ import unicode_literals

from django.contrib import admin

from mailer.models import Message, DontSendEntry, MessageLog


def show_to(message):
    try:
        if message.to:
            return message.to
    except AttributeError as e:
        pass
    return ", ".join(message.to_addresses)
show_to.short_description = "To"  # noqa: E305


class MessageAdminMixin(object):

    def plain_text_body(self, instance):
        email = instance.email
        if hasattr(email, 'body'):
            return email.body
        else:
            return "<Can't decode>"


class MessageAdmin(MessageAdminMixin, admin.ModelAdmin):

    list_display = ["id", show_to, "subject", "when_added", "priority"]
    readonly_fields = ['plain_text_body']
    date_hierarchy = "when_added"
    list_filter = ['priority', ]


class DontSendEntryAdmin(admin.ModelAdmin):

    list_display = ["to_address", "when_added"]


class MessageLogAdmin(MessageAdminMixin, admin.ModelAdmin):

    list_display = ["id", show_to, "subject", "message_id", "when_attempted", "result", "account"]
    list_filter = ["result", "account"]
    date_hierarchy = "when_attempted"
    readonly_fields = ['plain_text_body', 'message_id']
    search_fields = ['message_id', 'account', 'to']


admin.site.register(Message, MessageAdmin)
admin.site.register(DontSendEntry, DontSendEntryAdmin)
admin.site.register(MessageLog, MessageLogAdmin)
