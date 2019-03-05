ENVIRONMENTS = ('test',
                'pre',
                'bank',
                'p2p',
               )
ENVIRONMENTS_ALIAS = {
                'test':'测试环境',
                'pre':'预发布环境',
                'bank':'生产bank环境',
                'p2p':'生产p2p环境',
                }

LOG_PATH = '/var/log/geniusalt'
SALT_FILE_ROOT = '/var/django_projects/geniusalt_project/genisalt-modules'
SALT_BIN = '/usr/bin/salt'
SALT_KEY_BIN = '/usr/bin/salt-key'

USE_ANSIBLE = True ### saltstack is used by default. Use ansible if this var is set to True.
ANSIBLE_PLAYBOOKS = '/var/django_projects/geniusalt_project/geniusalt-modules'
ANSIBLE_BIN = '/usr/local/python3/bin/ansible-playbook'
ANSIBLE_MODULE_INIT = 'main.yml'
ANSIBLE_SSH_USER_KEY = '/root/.ssh/id_rsa'
