from django.contrib import admin

from mailer.models import Message, DontSendEntry, MessageLog


class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "to_addresses", "subject", "when_added", "priority"]

    def has_add_permission(self, request):
        return False


class DontSendEntryAdmin(admin.ModelAdmin):
    list_display = ["to_address", "when_added"]

    def has_add_permission(self, request):
        return False


class MessageLogAdmin(admin.ModelAdmin):
    list_display = ["id", "to_addresses", "subject", "when_attempted", "result"]

    def has_add_permission(self, request):
        return False


admin.site.register(Message, MessageAdmin)
admin.site.register(DontSendEntry, DontSendEntryAdmin)
admin.site.register(MessageLog, MessageLogAdmin)
