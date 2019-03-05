from geniusalt.models import Cluster, Node, Instance
from .common import *


class ClusterOperator(Operator):
    fields_defination = {
        'name':        StrType(),
        '--short':     BoolType(),
        'nodes':       ListType(item_type=ObjectType(Node)),
        'instances':   ListType(item_type=ObjectType(Instance)),
    }

    @fields_validator(f_required=['name'],f_optional=['nodes', 'instances'],obj_model=Cluster, check_true=False)
    def add(self):
        nodes = self.pop_field('nodes', default=[])
        instances = self.pop_field('instances', default=[])
        obj = Cluster(**self.checked_parameters)
        obj.save()
        if nodes:
            obj.node_set.set(nodes)
        if instances:
            _count = len(instances)
            if _count == 1:
                obj.bind_instance = instances[0]
            else:
                self.message += "WARNING: multi instances are not allowed. To set bind_instance ignored. "
        obj.save()
        self.message += "To add Cluster '{}' succeeded.\n".format(self.checked_parameters['name'])

    @fields_validator(f_required=['name'], f_optional=[], obj_model=Cluster)
    def delete(self):
        self.obj.delete()
        self.message = "To delete Cluster '{}' succeeded.\n".format(self.checked_parameters['name'])

    @fields_validator(f_required=['name'], f_optional=[], obj_model=Cluster)
    def lock(self):
        self.obj.is_lock = 1
        self.obj.save()
        self.message = "To lock Cluster '{}' succeeded.\n".format(self.checked_parameters['name'])

    @fields_validator(f_required=['name'], f_optional=[], obj_model=Cluster)
    def unlock(self):
        self.obj.is_lock = 0
        self.obj.save()
        self.message = "To unlock Cluster '{}' succeeded.\n".format(self.checked_parameters['name'])

    @fields_validator(f_required=['name'], f_optional=['instances', 'nodes'], obj_model=Cluster)
    def clusterSet(self):
        nodes = self.pop_field('nodes', default=[])
        instances = self.pop_field('instances', default=[])
        if not (nodes or instances):
            return self.set_error("ERROR: clusterSet requires nodes or instances specified.")
        if nodes:
            self.obj.node_set.set(nodes)
        if instances:
            _num = len(instances)
            if _num == 1:
                self.obj.bind_instance = instances[0]
            else:
                return self.set_error("ERROR: multi-instances are not allowed with clusterSet.")

        self.obj.save()
        self.message = "To set Cluster '{}' succeeded.\n".format(self.checked_parameters['name'])

    @fields_validator(f_required=[], f_optional=['name', '--short'], check_obj_exists=False)
    def show(self):
        queryset = self._get_queryset(Cluster)
        if queryset is not None:
            self.data = self._data_show(queryset)
