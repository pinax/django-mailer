from django.conf.urls.defaults import *
from django.contrib import admin

urlpatterns = patterns('',
    # Example:
    # (r'^mailerdev/', include('mailerdev.foo.urls')),
    
    (r'^admin/(.*)', admin.site.root),
)
