from django.conf.urls import url
from .api.urls import urlpatterns as url_part1
from .get_file_api.urls import urlpatterns as url_part2

app_name = 'geniusalt'
urlpatterns =  url_part1 + url_part2
