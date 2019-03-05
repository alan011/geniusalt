from geniusalt.models import Node, Instance, Module, Cluster
from .common import *

class RelationOperator(Operator):
    fields_defination = {
        'nodes':              ListType(item_type=ObjectType(Node)),
        'instances':          ListType(item_type=ObjectType(Instance)),
        'bind_modules':       ListType(item_type=ObjectType(Module)),
        'bind_instances':     ListType(item_type=ObjectType(Instance)),
        'included_instances': ListType(item_type=ObjectType(Instance)),
        'clusters':           ListType(item_type=ObjectType(Cluster)),
    }

    @fields_validator(f_required=[],f_optional=['instances', 'included_instances'],check_obj_exists=False)
    def _include(self, method_name='include'):
        ### To check instances.
        instances          = self.checked_parameters['instances']
        included_instances = self.checked_parameters['included_instances']
        for i_obj in instances:
            if i_obj in included_instances:
                return self.set_error("ERROR: Instance obj '{}' cannot {} itself".format(i_obj.name, method_name))

        ### To set relationship.
        _mapper = {'include':'add', 'exclude':'remove'}
        for i_obj in instances:
            getattr(i_obj.included_instances, _mapper[method_name])(*included_instances)
            i_obj.save()

        self.message = "To set instances {} to {} other instances {} succeed\n".format(','.join(self.parameters['instances']), method_name, ','.join(self.parameters['included_instances']))

    @fields_validator(f_required=[],f_optional=['nodes', 'clusters', 'bind_modules', 'bind_instances'],check_obj_exists=False)
    def _bind(self, method_name='bind'):
        ### To get objects.
        modules   = self.pop_field('bind_modules', default=[])
        instances = self.pop_field('bind_instances', default=[])
        nodes     = self.pop_field('nodes', default=[])
        clusters  = self.pop_field('clusters', default=[])

        if not (modules or instances):
            return self.set_error("ERROR: Field 'bind_modules' or 'bind_instances' is required.")
        if not (nodes or clusters):
            return self.set_error("ERROR: Field 'nodes' or 'clusters' is required.")
        if nodes and clusters:
            return self.set_error("ERROR: Field 'nodes' and 'clusters' cannot be specified together.")
        if clusters:
            if len(instances) != 1:
                return self.set_error("ERROR: multi-instances are not allowed to bind to the same clusters.")
            if modules:
                return self.set_error("ERROR: modules cannot bind to cluster.")

        ### To set nodes.
        _mapper = {'bind':'add', 'unbind':'remove'}
        if nodes:
            if method_name == 'bind':
                for i_obj in filter(lambda i: i.module_belong not in modules, instances):
                    modules.append(i_obj.module_belong)
            for n_obj in nodes:
                if modules:
                    getattr(n_obj.bind_modules, _mapper[method_name])(*modules)
                if instances:
                    getattr(n_obj.bind_instances, _mapper[method_name])(*instances)
                n_obj.save()
            self.message = "To {} objects '{}' to Nodes '{}' succeed.\n" .format(method_name,','.join(o.name for o in modules + instances), ','.join(self.parameters['nodes']))
        if clusters:
            instance = instances[0]
            for c in clusters:
                if method_name == "bind" and c.bind_instance != instance:
                    c.bind_instance = instance
                    c.save()
                if method_name == 'unbind' and c.bind_instance == instance:
                    c.bind_instance = None
                    c.save()
                # for n_obj in c.node_set.all():
                #     getattr(n_obj.bind_modules, _mapper[method_name])(c.bind_instance.module_belong)
                #     getattr(n_obj.bind_instances, _mapper[method_name])(c.bind_instance)
                #     n_obj.save()
            self.message = "To {} instance '{}' to Clusters '{}' succeed.\n" .format(method_name,instance.name, ','.join(self.parameters['clusters']))


    @fields_validator(f_required=['nodes', 'clusters'],f_optional=[],check_obj_exists=False)
    def _joinCluster(self, method_name='join'):
        nodes    = self.pop_field('nodes',    default=[])
        clusters = self.pop_field('clusters', default=[])
        _mapper  = {'join':'add', 'unjoin':'remove'}
        for n_obj in nodes:
            getattr(n_obj.cluster_joined, _mapper[method_name])(*clusters)
        n_obj.save()
        self.message = "To {} objects '{}' to Clusters '{}' succeed.\n" .format(method_name, ','.join(self.parameters['nodes']), ','.join(o.name for o in clusters))

    def bind(self):
        """
        To bind Module or Instance to Nodes. Only bind in DB, not really to install objects for a real host.
        """
        self._bind()

    def unbind(self):
        """
        To unbind Module or Instance from Nodes.
        """
        self._bind(method_name='unbind')

    def include(self):
        """
        To set Instance objects to include other Instance object.
        """
        self._include()

    def exclude(self):
        """
        To set Instance objects to exclude other Instance object.
        """
        self._include(method_name='exclude')

    def joinCluster(self):
        self._joinCluster()

    def unJoinCluster(self):
        self._joinCluster(method_name='unjoin')
