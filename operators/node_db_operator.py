from geniusalt.models import Node, Instance
from .common import *
from geniusalt.config import SALT_KEY_BIN, USE_ANSIBLE
from itertools import islice
import os, re


class NodeOperator(Operator):
    fields_defination = {
        'name':        StrType(),
        'environment': ChoiceType(*Operator._ENVIRONMENTS),
        '--short':     BoolType(),
        '--from-node':   ObjectType(Node),
    }

    @fields_validator(f_required=['name'],f_optional=['environment'],obj_model=Node, check_true=False)
    def add(self):
        obj = Node(**self.checked_parameters)
        obj.save()
        self.message = "To add Node '{}' succeeded.\n".format(self.checked_parameters['name'])

    @fields_validator(f_required=['name', '--from-node'], f_optional=[], obj_model=Node, check_true=False)
    def clone(self):
        _chp = self.checked_parameters
        node_obj = _chp['--from-node']
        instances = list(node_obj.bind_instances.all())
        modules   = list(node_obj.bind_modules.all())
        clusters  = list(node_obj.cluster_joined.all())
        node_obj.id = None
        node_obj.name = _chp['name']
        node_obj.save()
        node_obj.bind_modules.set(modules)
        node_obj.bind_instances.set(instances)
        node_obj.cluster_joined.set(clusters)
        node_obj.save()
        self.message = "To clone a new Node '{}' to from node '{}' succeeded.".format(self.parameters['name'], self.parameters['--from-node'])

    @fields_validator(f_required=['name'], f_optional=[], obj_model=Node)
    def delete(self):
        self.obj.delete()
        self.message = "To delete Node '{}' succeeded.\n".format(self.checked_parameters['name'])

    @fields_validator(f_required=['name', 'environment'], f_optional=[], obj_model=Node)
    def environmentSet(self):
        self.obj.environment = self.checked_parameters['environment']
        self.obj.save()
        self.message = "To set Node '{}' to environment '{}' succeeded.\n".format(self.obj.name, self.checked_parameters['environment'])

    @fields_validator(f_required=['name'], f_optional=[], obj_model=Node)
    def lock(self):
        self.obj.is_lock = 1
        self.obj.save()
        self.message = "To lock Node '{}' succeeded.\n".format(self.checked_parameters['name'])

    @fields_validator(f_required=['name'], f_optional=[], obj_model=Node)
    def unlock(self):
        self.obj.is_lock = 0
        self.obj.save()
        self.message = "To unlock Node '{}' succeeded.\n".format(self.checked_parameters['name'])

    @fields_validator(f_required=[], f_optional=['name', '--short'], check_obj_exists=False)
    def show(self):
        queryset = self._get_queryset(Node)
        if queryset is not None:
            self.data = self._data_show(queryset)

    def scan(self):
        """
        To auto-add Nodes by scanning host IDs in saltstack master.
        If host ID was not accepted by saltstack master, accept it.
        """
        if USE_ANSIBLE:
            return self.set_error("ERROR: 'scan' for nodes is not allowed to use when api-server's config parameter 'USE_ANSIBLE' is set to 'True'. Use 'add' instead.")

        if not os.path.isfile(SALT_KEY_BIN):
            return self.set_error("ERROR: Bin file '{}' is not found. This may because salt-master is not installed on this host properly.".format(SALT_KEY_BIN),http_status=500)

        with os.popen('{} -l acc'.format(SALT_KEY_BIN)) as fa,  os.popen('{} -l un'.format(SALT_KEY_BIN)) as fu:
            _, *nodes = map(lambda line: line.strip(), fa)
            for node_name in islice(fu, 1, None):
                os.system('{} -a {} -y'.format(SALT_KEY_BIN, node_name.strip()))
                nodes.append(node_name.strip())

        for node in nodes:
            obj = self.get_object(Node, node)
            if obj:
                self.message += "Duplicated node '{}', ignored.\n".format(node)
            else:
                new_obj = Node(name=node)
                new_obj.save()
                self.message += "Add new node: {}\n".format(node)
