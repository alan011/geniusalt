from django.conf import settings
import os

GET_FILE_SCRIPT = os.path.join(settings.BASE_DIR, "geniusalt/get_file_api/scripts/get_file.sh")
LIST_DIR_SCRIPT = os.path.join(settings.BASE_DIR, "geniusalt/get_file_api/scripts/list_dir.sh")

MAX_FILE_SIZE = 104857600  # file will always be download when size is bigger than this setting value.

HOSTS_ALLOW = {
    "10.0.1.179": {
        "port":65532,
        "allowed_dirs":['/data1/Dispatch/log'],
    },
    "10.0.1.19": {
        "port":65532,
        "allowed_dirs":['/data1/Dispatch/log'],
    },
    "10.0.2.17": {
        "port":65532,
        "allowed_dirs":['/data1/Dispatch/log'],
    },
    "10.0.2.11": {
        "port":65532,
        "allowed_dirs":['/data1/Dispatch/log'],
    },
    "10.199.199.16": {
        "port":65532,
        "allowed_dirs":['/data1/log/nginx'],
    },
    "10.199.199.17": {
        "port":65532,
        "allowed_dirs":['/data1/log/nginx'],
    },
}
