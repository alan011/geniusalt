from geniusalt.models import *
from .common import *

class InstanceOperator(Operator):
    fields_defination = {
        'name':          StrType(r'^[a-zA-Z]+[0-9a-zA-Z_\-\.]*$'),
        'environment':   ChoiceType(*Operator._ENVIRONMENTS),
        'pillar':        DictType(key_type=StrType(r'^[a-zA-Z]+[0-9a-zA-Z_\-]*$')),
        'pillar_name':   StrType(r'^[a-zA-Z]+[0-9a-zA-Z_\-]*$'),
        'module_belong': ObjectType(Module),
        'nodes':         ListType(item_type=ObjectType(Node)),
        '--short':       BoolType()
    }

    def _check_pillar(self, module_obj, pillar, legal_check_only=False):
        legal_pillars = module_obj.pillar_required + module_obj.pillar_optional
        _illegal      = pillar.keys() - legal_pillars
        _req          = module_obj.pillar_required - pillar.keys()
        if _illegal:
            return self.set_error("ERROR: Illegal pillar found: '{}'.".format(', '.join(_illegal)), return_value=False)
        if (not legal_check_only) and _req:
            return self.set_error("ERROR: pillar '{}' is required by module '{}'.".format(', '.join(_req), module_obj.name), return_value=False)
        return True

    def _fill_pillar(self, instance_obj, pillar, environment='', node=''):
        for p in pillar:
            attrs = {'pillar_name':p,
                    'pillar_value': str(pillar[p]),
                    'instance_belong': instance_obj,
                    'environment': environment,
                    'node': node,
                    }
            p_obj = Pillar(**attrs)
            try:
                p_obj.save()
            except:
                self.message += "WARNING: To fill pillar '{}' for instance '{}' failed. Instance may not work as you expected. Please remember to use 'pillarSet' method to reset this pillar appropriately later!\n".format(p, instance_obj.name)


    @fields_validator(f_required=['name', 'module_belong'],
                      f_optional=['pillar', 'environment'],
                      obj_model=Instance, check_true=False)
    def add(self):
        ### To remove attributes for Pillar, and check it.
        _chp = self.checked_parameters
        environment = self.pop_field('environment', default='')
        pillar      = self.pop_field('pillar',      default={})
        if self._check_pillar(_chp['module_belong'],pillar):
            obj = Instance(**_chp)
            obj.save()
            self.message = "To add Instance '{}' succeeded.\n".format(_chp['name'])

            ### To fill pillar for this instance.
            self._fill_pillar(obj, pillar, environment)


    @fields_validator(f_required=['name'], f_optional=[], obj_model=Instance)
    def delete(self):
        self.obj.delete()
        self.message = "To delete Instance '{}' succeeded.\n".format(self.parameters['name'])


    @fields_validator(f_required=['name', 'pillar'], f_optional=['environment', 'nodes'], obj_model=Instance)
    def pillarSet(self):
        _chpl       = self.checked_parameters['pillar']
        environment = self.pop_field('environment', default='')
        nodes       = self.pop_field('nodes', default=[])

        if not self._check_pillar(self.obj.module_belong, _chpl, legal_check_only=True): return
        if environment and nodes:
            return self.set_error("ERROR: 'environment' and 'nodes' cannot be specific together when using function 'pillarSet'.")

        ### environment specific
        if not nodes:
            ### To set value for existed pillars
            pillar_queryset = self.obj.pillars.filter(environment = environment)
            for p_obj in filter(lambda p_obj: p_obj.pillar_name in _chpl, pillar_queryset):
                p_obj.pillar_value = _chpl.pop(p_obj.pillar_name)
                p_obj.save()
            ### To add new pillar objects remain in _chpl.
            self._fill_pillar(self.obj, _chpl, environment=environment)
        ### nodes specific
        else:
            for node in nodes:
                pillar_queryset = self.obj.pillars.filter(node = node.name)
                for p_obj in filter(lambda p_obj: p_obj.pillar_name in _chpl, pillar_queryset):
                    p_obj.pillar_value = _chpl.pop(p_obj.pillar_name)
                    p_obj.save()
                ### To add new pillar objects remain in _chpl.
                self._fill_pillar(self.obj, _chpl, node=node.name)

        ### End.
        self.message += "To set pillar of instance '{}' succeeded.\n".format(self.obj.name)


    @fields_validator(f_required=['name', 'pillar_name'], f_optional=['environment', 'nodes'], obj_model=Instance)
    def pillarDel(self):
        _chp = self.checked_parameters
        environment = self.pop_field('environment', default='')
        nodes       = self.pop_field('nodes', default=[])
        if environment and nodes:
            return self.set_error("ERROR: 'environment' and 'nodes' cannot be specific together when using function 'pillarSet'.")
        if nodes:
            self.message = ''
            to_delete_pillar = []
            for node in nodes:
                pillar_filter = {'node' : node.name, 'pillar_name' : _chp['pillar_name'],}
                ### To get pillar objects of this instance.
                pillar_queryset = self.obj.pillars.filter(**pillar_filter)
                if not pillar_queryset.exists():
                    return self.set_error("ERROR: Instance '{}' has no such a pillar '{}' specified with node '{}'.".format(self.obj.name, _chp['pillar_name'], node.name))

                ### Do deleting.
                for p_obj in pillar_queryset:
                    to_delete_pillar.append(p_obj)
            for p_obj in to_delete_pillar:
                p_obj.delete()

            self.message +=  "To delete pillar '{}' of instance '{}' succeeded, which specified with nodes '{}' .\n".format (_chp['pillar_name'], self.obj.name, ','.join(node.name for node in nodes))

        else:
            pillar_filter = {'environment' : environment, 'pillar_name' : _chp['pillar_name'],}

            ### To get pillar objects of this instance.
            pillar_queryset = self.obj.pillars.filter(**pillar_filter)
            if not pillar_queryset.exists():
                return self.set_error("ERROR: Instance '{}' in environment '{}' has no such a pillar '{}'.".format(self.obj.name, environment, _chp['pillar_name']))

            ### Do deleting.
            for p_obj in pillar_queryset:
                p_obj.delete()

            ### End.
            self.message = "To delete pillar '{}' of instance '{}' succeeded in environment '{}'.\n".format (_chp['pillar_name'], self.obj.name, environment)


    @fields_validator(f_required=['name'], f_optional=[], obj_model=Instance)
    def lock(self):
        self.obj.is_lock = 1
        self.obj.save()
        self.message = "To lock Instance '{}' succeeded!\n".format(self.parameters['name'])


    @fields_validator(f_required=['name'], f_optional=[], obj_model=Instance)
    def unlock(self):
        self.obj.is_lock = 0
        self.obj.save()
        self.message = "To unlock Instance '{}' succeeded!\n".format(self.parameters['name'])

    @fields_validator(f_required=[], f_optional=['name', '--short'], check_obj_exists=False)
    def show(self):
        queryset = self._get_queryset(Instance)
        if queryset is not None:
            self.data = self._data_show(queryset)

    @fields_validator(f_required=['name'], f_optional=['--short'], obj_model=Instance)
    def showBind(self):
        self.data = self._data_show(self.obj.node_set.all())
