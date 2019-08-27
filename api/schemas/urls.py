from django.conf.urls import url

from api.schemas import views

app_name = 'osf'

urlpatterns = [
    url(r'^registrations/$', views.RegistrationSchemaList.as_view(), name=views.RegistrationSchemaList.view_name),
    url(r'^registrations/(?P<schema_id>\w+)/$', views.RegistrationSchemaDetail.as_view(), name=views.RegistrationSchemaDetail.view_name),
    url(r'^files/$', views.FileMetadataSchemaList.as_view(), name=views.FileMetadataSchemaList.view_name),
    url(r'^files/(?P<schema_id>\w+)/$', views.FileMetadataSchemaDetail.as_view(), name=views.FileMetadataSchemaDetail.view_name),
]
