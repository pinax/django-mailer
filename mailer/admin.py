from django.contrib import admin

from mailer.models import Message, DontSendEntry, MessageLog, Queue


def show_to(message):
    return ", ".join(message.to_addresses)
show_to.short_description = "To"


class QueueAdmin(admin.ModelAdmin):
    fields = ['name', 'mail_enabled', 'metadata']
    list_display = ['name', 'mail_enabled']

class MessageAdminMixin(object):

    def plain_text_body(self, instance):
        email = instance.email
        if hasattr(email, 'body'):
            return email.body
        else:
            return "<Can't decode>"


class MessageAdmin(MessageAdminMixin, admin.ModelAdmin):

    list_display = ["id", show_to, "subject", "when_added", "priority", "queue"]
    readonly_fields = ['plain_text_body']


class DontSendEntryAdmin(admin.ModelAdmin):

    list_display = ["to_address", "when_added"]


class MessageLogAdmin(MessageAdminMixin, admin.ModelAdmin):

    list_display = ["id", show_to, "subject", "when_attempted", "result"]
    readonly_fields = ['plain_text_body']

admin.site.register(Message, MessageAdmin)
admin.site.register(DontSendEntry, DontSendEntryAdmin)
admin.site.register(MessageLog, MessageLogAdmin)
admin.site.register(Queue, QueueAdmin)
