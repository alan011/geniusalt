from django.db import models
from jsonfield import JSONField
from collections import OrderedDict
from geniusalt.config import ENVIRONMENTS

YES_or_NO=((0,'否'),(1,'是'))

class AuthToken(models.Model):
    username        = models.CharField('用户名称',max_length=8, default='', unique=True)
    token           = models.CharField('用户TOKEN',max_length=64, default='', unique=True)
    sign_date       = models.DateTimeField('注册日期',auto_now_add=True)
    expired_time    = models.IntegerField('有效期限',default=86400) ### Defautl is One day. '0' means never expired.

class Module(models.Model):
    id              = models.AutoField('ID',primary_key=True)
    name            = models.CharField('模块名称',max_length=128, default='', unique=True)
    pillar_required = JSONField(default=[])
    pillar_optional = JSONField(default=[])
    lock_count      = models.IntegerField('锁定计数', default='0')

    def __str__(self):
        return self.name

    @property
    def attrs(self):
        _attrs = OrderedDict()
        _attrs["name"] = self.name
        _attrs["lock_count"] = self.lock_count
        _attrs["pillar_required"] = self.pillar_required
        _attrs["pillar_optional"] = self.pillar_optional
        return _attrs

class Instance(models.Model):
    id                = models.AutoField('ID',primary_key=True)
    name              = models.CharField('子模块名称',max_length=128, default='', unique=True)
    module_belong     = models.ForeignKey('Module', on_delete=models.CASCADE, related_name="instances")
    is_lock           = models.IntegerField('是否锁定', choices=YES_or_NO, default='0')
    included_instances= models.ManyToManyField('self', symmetrical=False)

    def __str__(self):
        return self.name

    def _pillar_attr(self, e):
        return 'pillar/{}'.format(e) if e else 'pillar'

    @property
    def attrs(self):
        _attrs = OrderedDict()
        _attrs["name"] = self.name
        _attrs["model_belong"] = self.module_belong.name
        _attrs["is_lock"] = self.is_lock
        _attrs["included_instances"] =[i.name for i in self.included_instances.all()]

        ### get pillars
        _pdict ={}
        for p_obj in self.pillars.all():
            pillar_attr = self._pillar_attr(p_obj.node) if p_obj.node else self._pillar_attr(p_obj.environment)
            if pillar_attr not in _pdict:
                _pdict[pillar_attr] = {}
            _pdict[pillar_attr][p_obj.pillar_name] = p_obj.pillar_value

        ### make an ordered display, which pillar/env ordered by config's order: 'ENVIRONMENTS'.
        for e in  [''] + list(ENVIRONMENTS):
            pillar_attr = self._pillar_attr(e)
            if pillar_attr in _pdict:
                _attrs[pillar_attr] = _pdict.pop(pillar_attr)
        for attr in _pdict:
            _attrs[attr] =  _pdict[attr]

        return _attrs

class Pillar(models.Model):
    id                = models.AutoField('ID',primary_key=True)
    pillar_name       = models.CharField('pillar名称', max_length=128, default='')
    pillar_value      = models.TextField('pillar值', default='')
    environment       = models.CharField('环境标签', max_length=128, default='')
    node              = models.CharField('专属节点', max_length=128, default='')
    instance_belong   = models.ForeignKey('Instance', on_delete=models.CASCADE, related_name="pillars")

class Cluster(models.Model):
    id              = models.AutoField('ID',primary_key=True)
    name            = models.CharField('集群名称',max_length=128, default='', unique=True)
    is_lock         = models.IntegerField('是否锁定', choices=YES_or_NO, default='0')
    bind_instance   = models.ForeignKey('Instance', on_delete=models.SET_NULL, related_name="bind_clusters", null=True)

    @property
    def attrs(self):
        _attrs = OrderedDict()
        _attrs["name"] = self.name
        _attrs["bind_instance"] = self.bind_instance.name if self.bind_instance else ''
        _attrs["is_lock"] = self.is_lock
        _attrs["members"] = [ n.name for n in self.node_set.all() ]
        return _attrs

    @property
    def pillar(self):
        _pillar = {n.name:{} for n in self.node_set.all()}
        if self.bind_instance:
            i_name = self.bind_instance.name
            m_name = self.bind_instance.module_belong.name
            for n in self.node_set.all():
                if n.pillar.get(m_name) and n.pillar.get(m_name).get(i_name):
                    _pillar[n.name].update(n.pillar[m_name][i_name])
        return _pillar

class Node(models.Model):
    id              = models.AutoField('ID',primary_key=True)
    name            = models.CharField('节点名称',max_length=128, default='', unique=True)
    environment     = models.CharField('所属环境', max_length=128, default='')
    is_lock         = models.IntegerField('是否锁定', choices=YES_or_NO, default='0')
    bind_modules    = models.ManyToManyField(Module)
    bind_instances  = models.ManyToManyField(Instance)
    cluster_joined  = models.ManyToManyField(Cluster)

    def __str__(self):
        return self.name

    def _fill_pillar(self, i_obj):
        instance_pillars = {}
        ### To get default pillar without environment set.
        for p_obj in i_obj.pillars.filter(environment='', node=''):
            instance_pillars[p_obj.pillar_name] = p_obj.pillar_value

        ### To update node's pillar with envrironment pillar objects.
        for p_obj in i_obj.pillars.filter(environment=self.environment, node='').exclude(environment=''):
            instance_pillars[p_obj.pillar_name] = p_obj.pillar_value

        ### To update node's pillar with node specified pillar objects.
        for p_obj in i_obj.pillars.filter(node=self.name):
            instance_pillars[p_obj.pillar_name] = p_obj.pillar_value

        return instance_pillars

    # def _bind_cluster_instance(self):
    #     pass

    @property
    def pillar(self):
        pl = {}
        for m_obj in self.bind_modules.all():
            pl[m_obj.name] = {}

        cluster_instances = [c.bind_instance for c in self.cluster_joined.all() if c.bind_instance]
        self_instances = [i for i in self.bind_instances.all() if i not in cluster_instances]
        for i_obj in self_instances + cluster_instances :
            module   = i_obj.module_belong.name
            instance = i_obj.name
            if module not in pl:
                pl[module] = {}
            pl[module][instance] = self._fill_pillar(i_obj)
            ### To fill pillars with included instances
            included_instances = i_obj.included_instances.all()
            if included_instances.exists():
                pl[module][instance]['__include__'] = {}
                for ii_obj in included_instances:
                    pl[module][instance]['__include__'][ii_obj.name] = self._fill_pillar(ii_obj)
        return pl

    @property
    def attrs(self):
        _attrs = OrderedDict()
        _attrs["name"] = self.name
        _attrs["is_lock"] = self.is_lock
        _attrs["environment"] = self.environment
        cluster_joined = self.cluster_joined.all()
        if cluster_joined.exists():
            _attrs["cluster_joined"] = [c.name for c in cluster_joined]
        _attrs["pillar"] = self.pillar
        return _attrs
