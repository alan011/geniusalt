from geniusalt.models import Node, Instance, Module, Cluster
from geniusalt.config import LOG_PATH, SALT_BIN, ANSIBLE_BIN, ANSIBLE_PLAYBOOKS, ANSIBLE_MODULE_INIT, ANSIBLE_SSH_USER_KEY, USE_ANSIBLE
from .relation_operator import RelationOperator
from .common import *

from threading import Thread
from datetime import datetime
from collections import OrderedDict
import os, json


class SimulPush(Thread):
    def __init__(self, node_name, pillar):
        self.node_name=node_name
        self.pillar = pillar
        self.push_result=None
        super().__init__()

    def run(self):
        self.push_result = self.pushOneNode()

    def get_playbook(mod):
        return os.path.join(ANSIBLE_PLAYBOOKS, mod, ANSIBLE_MODULE_INIT)

    def pushOneNode(self):
        ### prepare log storage.
        log_dir  = os.path.join(LOG_PATH, self.node_name)
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)
        _file    = 'push_at_{:%Y-%m-%d_%H%M%S}.log'.format(datetime.now())
        log_file = os.path.join(log_dir, _file)

        ### make the cmdline string.
        _cmd     = ANSIBLE_BIN if USE_ANSIBLE else SALT_BIN
        _node    = self.node_name
        _modules = ','.join(self.pillar.keys())
        _pillar  = json.dumps(self.pillar)

        if USE_ANSIBLE:
            log_ret = []
            for mod in self.pillar:
                for instance in self.pillar[mod]:
                    log_ret.append("----> push log for instance: {}".format(instance))

                    _modules = os.path.join(ANSIBLE_PLAYBOOKS, mod, ANSIBLE_MODULE_INIT)
                    _pillar  = json.dumps(self.pillar[mod][instance])
                    cmd_line =  '{} -i {}, {} -e \'{}\' --private-key={}'.format(_cmd, _node, _modules, _pillar, ANSIBLE_SSH_USER_KEY)

                    print("\n===> ansible-playbook: " + cmd_line)
                    with os.popen(cmd_line) as stream:
                        for line in stream:
                            log_ret.append(line)
            with open(log_file,'at') as log_file_o:
                log_file_o.writelines(log_ret)
            return log_ret
        else:
            cmd_line = '{} {} state.sls {} pillar=\'{}\''.format(_cmd, _node, _modules, _pillar)

            ### do salt push and write results to log file.
            print("\n===> saltstack: " + cmd_line)
            with open(log_file,'at') as log_file_o, os.popen(cmd_line) as stream:
                log_ret = [line for line in stream]
                log_file_o.writelines(log_ret)
                return log_ret



class PushOperator(Operator):
    fields_defination = {
        'nodes':            ListType(item_type=ObjectType(Node)),
        'clusters':         ListType(item_type=ObjectType(Cluster)),
        'bind_modules':     ListType(item_type=ObjectType(Module)),
        'bind_instances':   ListType(item_type=ObjectType(Instance)),
        '--only-module':    BoolType(),
        '--all-instances':  BoolType(),
        # '--checkself':      BoolType(),
    }

    def _check_lock(self, objects, object_type, lock_field='is_lock'):
        for o in objects:
            if getattr(o, lock_field) != 0:
                return self.set_error("ERROR: Push action aborted because {} '{}' has been locked.".format(object_type,o.name))
        return objects

    @fields_validator(f_required=[],f_optional=['nodes', 'clusters', 'bind_modules', 'bind_instances', '--only-module', '--all-instances'],
               check_obj_exists=False)
    def push(self):
        """
        To push Module or Instance to Nodes. This makes the real installation for a real host.
        Main logic:
            If no module and instance specified, all objects bound on these nodes will be pushed. If you want to push all modules without any instance, use '--only-module'.
            If any module or instance specified, only the specified modules or instances will be pushed to nodes, not all objects bound on nodes.
            If only modules specified, modules will be pushed without any instances. If you want to push all instances in  modules, use '--all-instances'.
        """
        _chp = self.checked_parameters

        ### If specified, to bind Modules or Instances to Nodes first.
        if self.parameters.get('bind_modules') or self.parameters.get('bind_instances'):
            if self.parameters.get('clusters'):
                return self.set_error("ERROR: implicit binding is not allowed for cluster objects. ")
            bind_operator = RelationOperator(self.parameters.copy())
            bind_operator.bind()
            if not bind_operator.result:
                return self.set_error(bind_operator.error_message, http_status=bind_operator.http_status)

        nodes = _chp.get('nodes')
        ### To check locked objects.
        clusters  = self._check_lock(self.pop_field('clusters', default=[]), 'CLuster')
        instances = self._check_lock(self.pop_field('bind_instances', default=[]), 'Instance')
        modules   = self._check_lock(self.pop_field('bind_modules', default=[]), 'Module', lock_field='lock_count')

        ### BoolType parameters usage checking.
        if (clusters is None) or (instances is None) or (modules is None):
            return None # Means some obj is locked. Push work aborted.
        if (instances or modules) and _chp['--only-module']:
            return self.set_error("ERROR: '--only-module' cannot be used with specified instances or modules.")
        if instances and _chp['--all-instances']:
            return self.set_error("ERROR: '--all-instances' cannot be used with specified instances.")

        if not (nodes or clusters):
            return self.set_error("ERROR: nodes or clusters must be provide.")
        if (nodes or instances or modules) and clusters:
            return self.set_error("ERROR: clusters cannot be pushed together with other objects. ")

        ### To make pillar dict for each node.
        pillar_total = {}
        if not clusters:
            for n in nodes:
                _np = n.pillar # pillars from all bound objects on this nodes with environment evaluated.

                if modules and _chp['--all-instances']:
                    _pillar = {m.name:_np[m.name] for m in modules}
                else:
                    _pillar = {m.name:{} for m in modules + [i.module_belong for i in instances]}

                for i in instances:
                    _m = i.module_belong.name
                    _pillar[_m][i.name] = _np[_m][i.name]

                if not _pillar: # Means no module or instance specified.
                    _pillar = {m:{} for m in _np} if  _chp['--only-module'] else _np

                pillar_total[n.name] = _pillar
        else:
            nodes = []
            for c in clusters:
                if not c.bind_instance:
                    return self.set_error("ERROR: Cluster '{}' did not bind to any instances, nothing to push.".format(c.name))
                for n in c.node_set.all():
                    nodes.append(n)
                    _m = c.bind_instance.module_belong.name
                    _i = c.bind_instance.name
                    _i_pillar = n.pillar[_m][_i]
                    _i_pillar.update({'__cluster__': c.pillar}) ### the main purpose
                    _pillar = {_m: {_i: _i_pillar}}
                    pillar_total[n.name] = _pillar

        ### check lock status of nodes to be pushed.
        nodes = self._check_lock(nodes, 'Node')

        ### To push objects to real hosts in multi-threading.
        thread_pool = {}
        self.pushlog = OrderedDict()
        for n in nodes:
            if not pillar_total[n.name]:
                self.pushlog[n.name] = ["Warning: Pushing ignored Node '{}', no object bound on this node.".format(n.name)]
            else:
                thread_pool[n.name] = SimulPush(n.name, pillar_total[n.name])
                thread_pool[n.name].start()
        for n_name in thread_pool:
            thread_pool[n_name].join()
            self.pushlog[n_name] = thread_pool[n_name].push_result
