设计说明
========


概要说明
--------

geniusalt是对saltstack的二次封装，用于linux集群环境下,后台应用运行环境的集中管理，配置文件的分发，以及灵活修改。

对saltstack做二次封装的目的，是为了简化使用，实现配置集中管理的WEB界面化。

应用的运行环境指的是，应用程序要正常运行，所依赖的软件包，中间件，以及应用特定的配置文件、目录、配置参数等。这些在“集控”概念出现之前，都需要由运维工程师登录服务器手动安装、配置。“集控”概念出现后，便可以由saltstack、puppet、ansible这些软件来集中管理、分发。但这些软件的使用上，可能出于通用性的考虑，对应用配置做任何修改，仍然需要运维工程师登录集控服务器去编辑配置模板。对WEB开发的支持并不是很友好，也很容易出错。故，本人不才，对saltstack做了这样的二次封装，用以进一步简化集控的管理工作，对WEB界面的定制开发，提供了友好的接口。

geniusalt中应用的配置由“模板(Module)”与”实例(Instance)“来管理，模板由saltstack的sls文件来定义；实例记录了一组pillar变量键值对，存储在数据库中，在执行配置推送的时候，以一个字典的形式回传给salt，这样pillar在模板的jinja2语法中做渲染，便可实现对应用配置文件的灵活修改，对所需软件包的灵活定制。由于pillar是存储在数据库中，很方便通过WEB界面来修改，从而可很方便地实现应用配置集中管理的WEB界面化。

geniusalt基于django框架开发，可作为独立服务以API的形式，对外提供使用；也可以以django app的形式，直接作为其他django项目的底层组件来使用。

对应的，以geniusalt的API为基础，我写了一套命令行工具--'gnsalt'，用以简化命令行的输入，美化展示数据（相比于单纯用curl调用API而言），是一个对运维工程师友好的命令行工具。参考项目：https://github.com/alan011/geniusalt-cli



数据模型
--------

在geniusalt中，有三个基本的数据对象，对应MySQL中的三张表：

* 模块（Module）

    对于绝大多数后台应用程序，都有它自己的运行环境依赖，比如有依赖tomcat的，有依赖weblogic的，有纯java自启动的服务，有依赖python环境的，有依赖php环境的等等。我们以这些运行环境类型（即“应用类型”）为单位，做一层抽象，即“模块(Module)”。

    Module的定义规则：在saltstack的file_root目录下，一个包含init.sls文件的目录，即被geniusalt认为是一个module.

    Module这一层，用于定义此应用类型的一些通用配置，比如，依赖包，中间件，中间件的通用配置文件等。一般，这些通用配置放在Module目录下即可。

    Module包含Instance，所以还需要定义用于渲染Instance的模板。一般，可以在Module的目录下再创建一个'instance'目录，用于编写以jinja2来渲染的Instance配置模板。

    Instance模板，需要用pillar变量来渲染，模板中到底支持哪些pillar变量，需要在Module中定义。geniusalt用Module目录下的pillar.json文件来定义pillar变量名。格式如下：
    ```
    {
        "pillar_required":["var1", "var2", ...],
        "pillar_optional":["var3", "var4", ...],
    }
    ```
    注意，geniusalt只认"pillar_required"与"pillar_optional"，顾名思义，一个表示定义实例时必须为实例提供变量，一个表示可选变量。这俩关键字，可只提供其中一个，其它非法关键字，将被geniusalt忽略。

    如未提供pillar.json文件，或者，其内容为空，则geniusalt认为此模块是不包含实例的模块。

    模板文件的编写范例，可参考项目：https://github.com/alan011/geniusalt-module-example

* 实例（Instance）

    Instance隶属于某一个Module，对应某一个应用类型下的具体的应用配置。

    Instance实际上就是一组pillar变量的键值对，用这组pillar来对Module中的.sls实例模板做渲染，从而生成此应用特有的配置文件，应用目录，安装包等。具体取决于用户如何在Module中编写实例模板，定义pillar变量。

* 节点（Node）

    对应saltstack管理控制的所有服务器。节点名称即是salt-keys命令返回的节点ID。一般以hostname作为节点名称。

    在geniusalt中，节点用于记录某台机器绑定了哪些模块与实例，即服务器需要安装的应用配置。

    模块与实例中记录的应用配置，将在salt-master上以主动推送的方式，下发到服务器。



配置推送
----------

定义好了模块和实例，geniusalt将调用salt-master的salt命令，以如下方式将应用配置推送到目标服务器：
```
/usr/bin/salt node_name state.sls <module1,module2,...> --pillar='{一个json字典，结构见下面示例}'

```
传给salt的pillar字典结构：
```
{
    "module1":{"instance1":{"pillar_var1":"pillar_value1", "pillar_var2":"pillar_value2",...},
            "instance2":{},
            ...
            },
    "module2":{...},
    ...
}
```
注意：编写模板用jinja2语言做渲染的时候，需要遵守这个pillar字典结构的约定。

应用配置的推送方式，分两种：

* 推送时不明确指定配置对象（即模块或实例）

    这种方式，需要我们先将配置对象绑定到某个节点，然后push这个节点，即可将这个节点上绑定的所有配置对象，推送到服务器。

* 推送时明确指定配置对象

    这种方式，要求我们在调用push接口时，提供要推送的模块或实例，push执行过程中，将仅推送明确指定的配置对象，而会忽略这个节点上已绑定的其他配置对象。当然，这会自动记录节点与配置对象的绑定关系。

从我目前的单位使用情况来看，绝大多数情况下都是使用明确指定配置对象的推送方式，这样可以最大限度的降低本次变更对同一台服务器下运行的其他不相关应用的影响。

具体如何推送，参考后面PushOperator的使用说明。


关于环境的考虑
_________

很多公司，运维团队会负责管理维护公司的所有开发项目。他们一般都会根据项目的开发周期，定义不同的应用运行环境，如开发测试环境(dev)，集成测试环境(sit)，压测环境（pt）, 准生产环境（uat）,生产环境（product）等等。同一个后台应用，在不同的环境下，配置文件的配置参数，可能是不同的。对应的，即是Instance的某个pillar变量，其值在不同的环境下，可能有不同的值。比如，tomcat的某个应用，在dev环境的xms需要设置为512m，在sit环境需要设置为1024m，在生产环境需要设置为2048m。

在geniusalt中，“环境”的区分，我这是这样考虑的：

* 一个节点（即一台服务器）属于某一个环境，不可同时属于多个环境：

    节点会有一个'environment'属性来记录它所隶属的环境。

* 模块层不区分环境

    模块层所管理的是通用的共性的配置，比如安装什么软件包，创建哪些目录，管理通用配置文件等。

* 在实例层来具体区分不同环境的配置参数的定义：

    没有明确指定环境的pillar变量，作为实例默认pillar。比如，设置某tomcat实例xms默认大小为512m；

    针对具体的环境，可以设置本环境需要的pillar，比如，在sit环境中，设置xms大小为1024m，在生产环境中，设置xms大小设置为2048m;

    这样，当推送这个实例到某个节点时，会根据节点的'environment'属性来决定使用哪个配置：如果节点是生产环境，xms则为2048m；如果节点是sit环境，xms则为1024m；如果是其他环境，因本例中没有对其他环境做明确设置，xms则使用默认的512m。

    在instance中默认pillar变量值被记录在'pillar'属性中，环境特定的值被记录在'pillar/<环境名称>'的属性中。

    环境名称，可以通过配置文件来定义：`geniusalt/config.py`。


安装
=========

geniusalt-apiserver用python3编写，在Django环境下运行，是一个相对独立的Django应用。

依赖系统环境：
    * OS: Linux各发行版本即可，不支持windows
    * python3
    * saltstack： 需要预先安装salt-master，安装方法请参考salt官网：https://repo.saltstack.com/#rhel

依赖python3软件包（pip安装即可）：
    * django: django-1.11以上即可
    * jsonfield

安装geniusalt-apiserver：

    下载源码包，将所有文件放在一个目录下，作为一个django的app放在django的工程目录即可，注意配置settings.py以及导入url，
    ```
    url路径：geniusalt/api/urls.py
    ```

启动服务，进入django的工程目录，执行以下命令：

```
~$ cd /path/to/your/django_project/
~$ nohup python3 ./manage.py runserver 0.0.0.0:10080 &
```



功能与操作器接口
=========

geniusalt根据其功能，将所有操作封装在以下五个操作器中：

* ModuleOperator
* InstanceOperator
* NodeOperator
* RelationOperator
* PushOperator

每个class接受一个parameters参数来生成一个操作器对象。parameters是一个参数字典，提供给每个操作方法使用。

下面的例子，展示了如何使用ModuleOperator添加一个Module

```
from geniusalt.operators import ModuleOperator

parameters = {'name':'tomcat',
            'pillar_required':['app_name','app_port'],
            'pillar_optional':[],
            }
module_operator = ModuleOperator(parameters=parameters)
module_operator.add()                         
### 每个操作方法都不接受任何参数，都返回None。操作结果与信息会设置在module_operator对应的属性中，后面会详细说明。

print(module_operator.result)       ### "True" 表示成功， "False"表示失败
print(module_operator.message)      ### 打印成功时，回传的信息
print(module_operator.err_message)  ### 打印失败时，回传的错误信息
```

本例中，parameters中的'name', 'pillar_required', 'pillar_optional'为ModuleOperator.add方法所支持的参数。

每个操作器会定义本操作器要使用的所有参数；操作器的方法，会声明本方法支持哪些操作器定义的参数。

每个操作器的操作方法本身，都不接受任何参数，都返回None，所有操作结果、信息、数据，都会设置在操作器的对应属性中。这样设计是为了API的统一调度分发，使用统一的URL，不用为每个方法都单独设计一个URL。

下面对各个操作器所支持的方法，方法所支持的参数，参数的校验规则，加以详细说明。


参数类型说明
----------

参数类型用于给operator传参时，用作数据合法性校验，有点类似Django的Form的校验功能，但校验规则更加精细化。

每种类型都必须支持check(field_value)方法，来做实际的校验工作；

若校验通过，返回对应的值、或数据对象，校验失败，则返回None。

geniusalt中，预定义了一下几种中参数类型：

* `BoolType(default=False)``

    布尔类型参数，默认指定了为True，不指定则为False。

    如想翻转这个默认逻辑，可以这样初始化：`BoolType(default=True)`，即表示不指定为True，指定了就为False。

    check方法返回True或False.

    一般Bool类型的参数名前面会加'--'，如'--instance', '--short'等参数名。

* `StrType(regex='.*')`

    字符串类型参数，初始化接受一个匹配正则表达式，用以限定参数值要匹配正则表达式。

    若不指定正则，则默认匹配所有字符。

* `ChoiceType(*choices)`

    选择型参数，初始化接受一个支持*解包的容器对象。用以限定参数值需是指定的值之一。

* `ObjectType(model, regex='.*')`

    数据对象类型参数，数据对象指的是节点、模块、实例等对象。初始化时，接受一个Model名称（Instance, Module, Node三个model之一），以及一个可选的正则表达式。

    表示参数值要是字符串，且匹配正则表达式，且能以`name=<参数值>`的方式在model中查到一个数据对象。

* `ListType(item_type=StrType())`


* `DictType(key_type=StrType(), val_type=StrType())`



ModuleOperator
----------

参数定义：

```
# 参数名:           参数值类型限定，
'name':            StrType(r'^[a-zA-Z]+[0-9a-zA-Z_\-]*$'),
'pillar_required': ListType(item_type=StrType(r'^[a-zA-Z]+[0-9a-zA-Z_\-]*$')),
'pillar_optional': ListType(item_type=StrType(r'^[a-zA-Z]+[0-9a-zA-Z_\-]*$')),
'--short':         BoolType(),
'--instance':      BoolType(),
```

支持方法：

* ModuleOperator.add

    add方法用于手动添加一个模块。pillar_required，pillar_optional这两个参数用于定义此模块所属实例所支持的pillar变量。

    支持必填参数：name；

    支持可选参数：pillar_required，pillar_optional


* ModuleOperator.scan

    scan方法用于通过扫描saltstack的file_root目录，来自动添加、更新一个模块。pillar_required，pillar_optional这两个参数需要定义在每个模块目录的pillar.json文件中。

    scan方法，不需要参数，故，初始化一个module_operator时，可不提供parameters参数。

* ModuleOperator.delete

    delete方法用于手动删除一个模块。

    支持必填参数：name；

    支持可选参数：无

* ModuleOperator.lock

    锁定一个模块，用于阻止对此模块相关配置的下发推送。执行此操作，会将module的lock_count属性 + 1， 当lock_count计数大于0时，认为模块已锁定。等于0时，认为未锁定。

    注意：当锁定一个模块后，这个模块下的所有实例，也会被同时阻止推送。

    支持必填参数：name；

    支持可选参数：无

* ModuleOperator.unlock

    对模块做解锁操作，将module对象的lock_count计数 - 1。注意，这里只是做减一操作，并不是直接归零，

    支持必填参数：name；

    支持可选参数：无


* ModuleOperator.show

    show方法用于显示模块。

    支持必填参数：无；

    支持可选参数：name, --short, --instance;

    name表示显示指定的模块，若不提供，表示显示所有模块。
    --short参数表示，只显示模块名称，不显示模块详情。默认要显示模块详情。下同
    --instance参数，表示同时显示此模块下包含的所有实例的名称列表。下同

* ModuleOperator.showBind

    用以显示已绑定了本模块的所有Node。显示的是Node信息，不是模块。

    支持必填参数：name；

    支持可选参数：--short, --instance;


InstanceOperator
-----------

参数定义：

```
# 参数名:         参数值类型限定，
'name':          StrType(r'^[a-zA-Z]+[0-9a-zA-Z_\-\.]*$'),
'environment':   ChoiceType(*Operator._ENVIRONMENTS),
'pillar':        DictType(key_type=StrType(r'^[a-zA-Z]+[0-9a-zA-Z_\-]*$')),
'pillar_name':   StrType(r'^[a-zA-Z]+[0-9a-zA-Z_\-]*$'),
'module_belong': ObjectType(Module),
'--short':       BoolType()
```

支持方法：

* InstanceOperator.add

    用来添加应用配置实例。

    支持必填参数：name, module_belong;

    支持可选参数：pillar, environment;

    name表示要添加的实例的名称，名称必须唯一，不能重复。

    module_belong表示此实例所属的模块。一个实例必须属于某一个已存在的模块，才能用pillar来渲染模块中的配置模板。

    pillar用于指定pillar字典，字典的内容，需被对应的模块支持，否则会报错。若模块定义了pillar_required变量，那么，未明确提供此参数、或字典内容不符合模块的pillar_required要求时，则会报错。

    environment用于指定pillar时，设定pillar的环境。需先提供pillar参数。

* InstanceOperator.delete

    用于删除实例。

    支持必填参数：name

    支持可选参数：无

    

NodeOperator
------------

参数定义：

```
# 参数名:       参数值类型限定，
'name':        StrType(),
'environment': ChoiceType(*Operator._ENVIRONMENTS),
'--short':     BoolType(),
```

支持方法：



RelationOperator
---------

参数定义：

```
# 参数名:              参数值类型限定，
'nodes':              ListType(item_type=ObjectType(Node)),
'instances':          ListType(item_type=ObjectType(Instance)),
'bind_modules':       ListType(item_type=ObjectType(Module)),
'bind_instances':     ListType(item_type=ObjectType(Instance)),
'included_instances': ListType(item_type=ObjectType(Instance)),
```

支持方法：


PushOperator
---------

参数定义：

```
# 参数名:            参数值类型限定，
'nodes':            ListType(item_type=ObjectType(Node)),
'bind_modules':     ListType(item_type=ObjectType(Module)),
'bind_instances':   ListType(item_type=ObjectType(Instance)),
'--only-module':    BoolType(),
'--all-instances':  BoolType(),
```

支持方法：



接口概述
=========

接口URL（此处以本地调用为例）：

```
http://localhost:10080/geniusalt/api/v1/ingress
```

* 调用方式：只能用POST方法

* POST data参数说明
    * data段， 应该传一个json格式的字典。
    * 三个必填参数: 'auth_token', 'action', 'object'

'auto_token'用于接口调用的认证。目前版本，还没有做详细的权限划分，只要token认证通过，就能调用apiserver进行所有操作。
token的管理，请参考后文的token_manager使用方法。
```
'auth_token':'dLqsTdRa.1Mk17F2smGvvWJwHJgmffiLyPw4iruh6Dtt6ROnwoLPVH68mlWIYynnoBae4L19Z' #<8位的用户名>.<64位的密文串>
```

'object'用以指定要操作的对象，支持以下value：
```
'module'    # 操作一个module对象，可以使用别名：'-m','mod'
'instance'  # 操作一个instance对象，可以使用别名：'-s','inst'
'node'      # 操作一个node对象，可以使用别名：'-n'
'relation'  # 表示一个关系操作,
'push'      # 表示一个push操作，即将配置对象应用到实际的服务器。
```

'action'表示要执行的具体操作，支持以下value：
```
'scan'            # 自动添加node或module, 对于module还可以自动更新pillar参数列表。
                  # 支持操作对象：module, node

'add'             # 手动添加节点，模块，或者实例
                  # 支持操作对象：node, module, instance

'delete'          # 删除node, module, instance. 可以使用别名: 'del'
                  # 支持操作对象：node, module, instance

'show'            # 获取对象信息。
                  # 支持操作对象：node, module, instance

'pillarSet'       # 设置instance的pillar属性的变量值。可以使用别名：'pset'
                  # 支持操作对象：instance

'pillarDel'       # 删除instance的pillar属性的变量。  可以使用别名：'pdel'
                  # 支持操作对象：instance

'environmentSet'  # 可设置node的environment属性。别名：'eset', 'envSet'
                  # 支持操作对象：node

'lock'            # 锁定一个节点，模块，或者实例
                  # 注意，对于module，是将其lock_count属性加1，其值可以大于1。非0即为锁定状态。
                  # 处于锁定状态的对象，不能被push到实际服务器。
                  # 支持操作对象：node, module, instance

'unlock'          # 解锁一个节点，模块，或者实例
                  # 注意，对于module的解锁，是将lock_count减1，不是直接解锁，当lock_count值为0时，才真正处于解锁状态。
                  # 支持操作对象：node, module, instance

'showBind'        # 用于查询一个instance或module被绑定到哪些node，将返回一个node列表。别名：'showb'
                  # 支持操作对象：module, instance

'include'         # 用于设置一个instance包含另外一个instance
                  # 支持操作对象：relation

'exclude'         # 解除一个instance对另外一个instance的包含关系
                  # 支持操作对象：relation

'bind'            # 将instance或module绑定到node
                  # 支持操作对象：relation

'unbind'          # 解除instance或module与node的绑定关系
                  # 支持操作对象：relation

'push'            # 推送配置对象module或instance到实际服务器
                  # 支持操作对象：push
```

举例说明
-----

下面，以curl作为调用方式，举例说明接口的功能与使用方法。

* scan功能

自动扫描module文件模板，添加module对象：
```
~$ curl -s 'http://127.0.0.1:10080/geniusalt/api/v1/ingress' -X POST \
        -H 'Content_Type: application/json' \
        -d '{
            "auth_token":"dLqsTdRa.1Mk17F2smGvvWJwHJgmffiLyPw4iruh6Dtt6ROnwoLPVH68mlWIYynnoBae4L19Z",
            "action":"scan",
            "object":"module"
            }'

```
