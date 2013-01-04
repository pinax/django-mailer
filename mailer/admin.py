from django.contrib import admin

from mailer.models import Message, DontSendEntry, MessageLog


class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "to_addresses", "subject", "when_added", "when_send", "priority"]


class DontSendEntryAdmin(admin.ModelAdmin):
    list_display = ["to_address", "when_added"]


class MessageLogAdmin(admin.ModelAdmin):
    list_display = ["id", "to_addresses", "subject", "when_attempted", "result"]


admin.site.register(Message, MessageAdmin)
admin.site.register(DontSendEntry, DontSendEntryAdmin)
admin.site.register(MessageLog, MessageLogAdmin)