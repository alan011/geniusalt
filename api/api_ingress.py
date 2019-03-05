from django.views.generic import View
from django.http          import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators      import method_decorator


import json

from geniusalt.operators import ModuleOperator, InstanceOperator, NodeOperator, RelationOperator, PushOperator, ClusterOperator
from .auth import authenticate

@method_decorator(csrf_exempt, name='dispatch')
class GeniusaltIngress(View):
    type_words = {
        ModuleOperator:   ['module', '-m', 'mod'],
        InstanceOperator: ['instance', '-i', 'inst'],
        NodeOperator:     ['node', '-n'],
        ClusterOperator:  ['cluster', '-c'],
        RelationOperator: ['relation'],
        PushOperator:     ['push'],
        }
    actions = {
        'scan':         {'operators':[ModuleOperator, NodeOperator,],'alias':[]},
        'add':          {'operators':[ModuleOperator, InstanceOperator, NodeOperator,ClusterOperator],'alias':[]},
        'clone':        {'operators':[NodeOperator], 'alias':[]},
        'delete':       {'operators':[ModuleOperator, InstanceOperator, NodeOperator,ClusterOperator],'alias':['del']},
        'show':         {'operators':[ModuleOperator, InstanceOperator, NodeOperator,ClusterOperator],'alias':[]},
        'pillarSet':    {'operators':[InstanceOperator,],'alias':['pset']},
        'pillarDel':    {'operators':[InstanceOperator,],'alias':['pdel']},
        'clusterSet':   {'operators':[ClusterOperator,],'alias':['cset']},
        'environmentSet':{'operators':[NodeOperator,],'alias':['eset', 'envSet']},
        'lock':         {'operators':[ModuleOperator, InstanceOperator, NodeOperator,ClusterOperator],'alias':[]},
        'unlock':       {'operators':[ModuleOperator, InstanceOperator, NodeOperator,ClusterOperator],'alias':[]},
        'showBind':     {'operators':[ModuleOperator,InstanceOperator],'alias':['showb']},
        'include':      {'operators':[RelationOperator,],'alias':[]},
        'exclude':      {'operators':[RelationOperator,],'alias':[]},
        'bind':         {'operators':[RelationOperator,],'alias':[]},
        'unbind':       {'operators':[RelationOperator,],'alias':[]},
        'joinCluster':  {'operators':[RelationOperator,],'alias':['joinc']},
        'unJoinCluster':{'operators':[RelationOperator,],'alias':['unjc']},
        'push':         {'operators':[PushOperator,],'alias':[]},
        }


    def json_load(self, decode_type='utf-8'):
        try:
            post_data   = json.loads(self.request.body.decode(decode_type))
        except:
            return HttpResponse("ERROR: To load json data failed.", status=400)
        if isinstance(post_data, dict):
            return post_data
        else:
            return HttpResponse("ERROR: Post data illegal.", status=400)

    def get(self, request, *args, **kwargs):
        return HttpResponse('ERROR: Get method is not allowed.', status=400)

    def post(self, request, *args, **kwargs):
        ### To check post data in JSON.
        post_data = self.json_load()
        if isinstance(post_data, HttpResponse):
            return post_data

        ### To authenticate request.
        if not authenticate(post_data):
            return HttpResponse("ERROR: Authentication failed.", status = 403)

        ### To dispatch operating methods by 'action' and 'object'.
        action = post_data.get('action')
        if not action:
            return HttpResponse("ERROR: 'action' field is required.", status=400)
        object_type = post_data.get('object')
        if not object_type:
            return HttpResponse("ERROR: 'object' field is required.", status=400)

        operator = None
        for method in self.actions:
            if action == method or action in self.actions[method]['alias']:  ### To filter out invalid actions
                operator_method = method
                for operator_class in self.type_words:
                    if object_type in self.type_words[operator_class]: ### To filter out invalid object_types
                        operator = operator_class(parameters = post_data)
        if operator is None:
            return HttpResponse("ERROR: 'action: {}' or 'object: {}' your provided is not supported.".format(action, object_type), status=400)

        ### To do the real work.
        getattr(operator, operator_method)()
        if operator.result:   ### True of False
            response_data = {"result":"SUCCESS", "message":str(operator.message)}
            if operator.data is not None:   ### for show* actions.
                response_data['data'] = operator.data
            if operator.pushlog is not None:
                response_data['pushlog'] = operator.pushlog
            return HttpResponse(json.dumps(response_data),content_type='application/json')
        else:
            return HttpResponse(str(operator.error_message), status=operator.http_status)
