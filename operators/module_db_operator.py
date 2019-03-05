from geniusalt.models import Module
from geniusalt.config import SALT_FILE_ROOT, ANSIBLE_PLAYBOOKS, USE_ANSIBLE, ANSIBLE_MODULE_INIT
from .common import *
from collections import OrderedDict
import os, json

class ModuleOperator(Operator):
    fields_defination = {
        'name':            StrType(r'^[a-zA-Z]+[0-9a-zA-Z_\-]*$'),
        'pillar_required': ListType(item_type=StrType(r'^[a-zA-Z]+[0-9a-zA-Z_\-]*$')),
        'pillar_optional': ListType(item_type=StrType(r'^[a-zA-Z]+[0-9a-zA-Z_\-]*$')),
        '--short':         BoolType(),
        '--instance':      BoolType(),
    }


    @fields_validator(f_required=['name'],f_optional=['pillar_required', 'pillar_optional'],obj_model=Module, check_true=False)
    def add(self):
        obj = Module(**self.checked_parameters)
        obj.save()
        self.message = "To add Module '{}' succeeded.\n".format(self.parameters['name'])


    @fields_validator(f_required=['name'], f_optional=[], obj_model=Module)
    def delete(self):
        self.obj.delete()
        self.message = "To delete Module '{}' succeeded.\n".format(self.parameters['name'])


    @fields_validator(f_required=['name'], f_optional=[], obj_model=Module)
    def lock(self):
        self.obj.lock_count += 1
        self.obj.save()
        self.message = "To lock Module '{}' succeeded.\n".format(self.parameters['name'])


    @fields_validator(f_required=['name'], f_optional=[], obj_model=Module)
    def unlock(self):
        if self.obj.lock_count > 0:
            self.obj.lock_count -= 1
        self.obj.save()
        _still_lock  = "Operation succeeded, but module '{}' is still locked by other operations.".format(self.parameters['name'])
        _unlock      = "TO unlock Module '{}' succeeded.".format(self.parameters['name'])
        self.message = _still_lock if self.obj.lock_count > 0 else _unlock

    @fields_validator(f_required=[], f_optional=['name', '--short', '--instance'], check_obj_exists=False)
    def show(self):
        queryset = self._get_queryset(Module)
        if queryset is not None:
            self.data = self._data_show(queryset, self.checked_parameters['--instance'])

    @fields_validator(f_required=['name'], f_optional=['--short'], obj_model=Module)
    def showBind(self):
        self.data = self._data_show(self.obj.node_set.all())

    def scan(self):
        """
        To auto-add modules by scanning .sls files in fileroot directory of saltstack master.
        If module name exists in DB and pillar definations changed, update the module.
        """
        _fd = self.fields_defination
        _fdpr, _fdpo, _fdn = _fd['pillar_required'], _fd['pillar_optional'], _fd['name']
        mod_scan = []

        ### To support ansible playbook.
        init_file = ANSIBLE_MODULE_INIT if USE_ANSIBLE else "init.sls"
        file_root = ANSIBLE_PLAYBOOKS   if USE_ANSIBLE else SALT_FILE_ROOT

        for m in filter(lambda d: os.path.isfile(os.path.join(file_root,d,init_file)), os.listdir(file_root)):
            config_file = os.path.join(file_root,m,'pillar.json')
            pd = {'pillar_required':[], 'pillar_optional':[]}
            if os.path.isfile(config_file):
                try:
                    _pd = json.load(open(config_file))
                    if not isinstance(_pd, dict):
                        raise TypeError
                    pd['pillar_required'] = _fdpr.check(self.pop_field('pillar_required',f_dict=_pd, default=[]), err=TypeError)
                    pd['pillar_optional'] = _fdpo.check(self.pop_field('pillar_optional',f_dict=_pd, default=[]), err=TypeError)
                    pd['pillar_required'].sort()
                    pd['pillar_optional'].sort()
                except:
                    return self.set_error("ERROR: File 'pillar.json' with invalid contents found in module '{}'.".format(m), http_status = 500)
                if _pd:
                    self.message += "WARNING: Illegal config options found in module '{}': '{}'.\n".format(m,','.join(pillar_config.keys()))
            # validate pillar names.
            if _fdn.check(m):
                _m_attrs = {'name':m}
                _m_attrs.update(pd)
                mod_scan.append(_m_attrs)
            else:
                self.message += "WARNING: Illegal module name '{}' has been ignored.\n".format(m)

        for m_dict in mod_scan:
            m_queryset = Module.objects.filter(name=m_dict['name'])
            if m_queryset.exists():
                ### To update the pillar definations.
                m_obj = m_queryset.get(name=m_dict['name'])
                _pr = m_obj.pillar_required
                _po = m_obj.pillar_optional
                _pr.sort()
                _po.sort()
                if _pr != m_dict['pillar_required'] or _po != m_dict['pillar_optional']:
                    m_obj.pillar_required = m_dict['pillar_required']
                    m_obj.pillar_optional = m_dict['pillar_optional']
                    m_obj.save()
                    self.message += "To update module '{}' successfully.\n".format(m_dict['name'])
                else:
                    self.message += "Ignore unchanged module: '{}'.\n".format(m_dict['name'])
            else:
                ### To add new module.
                m_obj = Module(**m_dict)
                m_obj.save()
                self.message += "To add new module '{}' successfully.\n".format(m_dict['name'])
