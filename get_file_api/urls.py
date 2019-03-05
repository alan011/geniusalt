from django.conf.urls import url
from .api_to_get_file import get_file, list_dir

urlpatterns =  [ url(r'^api/v1/getfile', get_file),
                url(r'^api/v1/listdir', list_dir),
                ]
