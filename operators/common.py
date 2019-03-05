import re
from geniusalt.config import ENVIRONMENTS
from .decorators import fields_validator

### To define all supported field_types for operaters.
class FieldType(object):
    """
    This is the Top class of all field types class.
    All sub-classes must define a `check(self, field_value, ...)` method to validate parameters of operators.
    This method returns the corresponding object if check was OK, or `None` if check failed.
    """
    pass

class BoolType(FieldType):
    """
    True or False. Default if False.
    """
    def  __init__(self ,default=False):
        self.default = default

    def check(self, field_value=None):
        if field_value is None:
            return self.default
        return bool(field_value)

class StrType(FieldType):
    """
    This field type requires that field value must be a string, and can be matched with 'self.regex'.
    'regex' can be provided at defining-time.
    If no 'regex' prodived, it will match any strings by default.
    """
    def __init__(self, regex='.*'):
        self.regex    = re.compile(regex)

    def check(self, field_value):
        _field_value = str(field_value)
        if self.regex.match(_field_value):
            return _field_value
        return None

class ChoiceType(FieldType):
    """
    This field type requires that field value must be one of 'self.choices'.
    'choices' must be provided with a set, a touple, or a list at defining-time.
    """
    def __init__(self, *choices):
        self.choices  = choices

    def check(self, field_value):
        if field_value in self.choices:
            return field_value
        return None


class ObjectType(StrType):
    """
    This field type requires that field value must be a StrType,
    and more, we can use it to get a data object from DB.
    'model' must be provided at defining-time.
    'regex' can be specified yet, if not, means any string is OK.

    Note: `check()` method uses 'name' to identify an object from data models,
          this requires data model must define a unique field: 'name'.
    """
    def __init__(self, model, regex='.*'):
        self.model = model
        super().__init__(regex)

    def check(self, field_value, field_name='name'):
        _field_value  = super().check(field_value)
        object_filter = {field_name: _field_value}
        if _field_value is not None:
            queryset = self.model.objects.filter(**object_filter)
            if len(queryset) == 1:
                return queryset.get(**object_filter)
        return None

class ListType(FieldType):
    """
    This field type requires field value must be a list.
    'item_type' could be instance of 'StrType', 'ChoiceType', or 'ObjectTpye'.
    """
    def __init__(self, item_type=StrType()):
        self.item_type = item_type

    def check(self, field_value, err=None):
        if isinstance(field_value, list):
            items = []
            for item in field_value:
                item_check = self.item_type.check(item)
                if item_check is None:
                    if err is not None:
                        raise err
                    else:
                        return None
                items.append(item_check)
            return items
        if err is not None:
            raise err

class DictType(FieldType):
    """
    This field type requires field value must be a dict.
    'key_type' could be an instance of 'StrType', 'ChoiceType', or 'ObjectTpye'.
    'val_type' could be an instance of 'StrType', 'ChoiceType', or 'ObjectTpye'.
    """
    def __init__(self, key_type=StrType(), val_type=StrType()):
        self.key_type = key_type
        self.val_type = val_type

    def check(self, field_value):
        if isinstance(field_value, dict):
            _dict = {}
            for key, val in field_value.items():
                key_check = self.key_type.check(key)
                val_check = self.val_type.check(val)
                if key_check is None or val_check is None:
                    return None
                _dict[key_check] = val_check
            return _dict
        return None

### Base operator. All operators must inherit from this operator class.
class Operator(object):
    _ENVIRONMENTS = ('',)+ENVIRONMENTS
    fields_defination = {}
    def __init__(self, parameters=None):
        self.parameters         = parameters if isinstance(parameters,dict) else {}
        self.checked_parameters = None # will be set in decorator: fields_validator
        self.result        = True
        self.message       = ''
        self.error_message = ''
        self.http_status   = 200
        self.data          = None # Will be set in show, showBind method.
        self.pushlog       = None # Will be set in push method.

    def get_object(self, model, object_name):
        queryset = model.objects.filter(name=object_name)
        if len(queryset) == 1:
            return queryset.get(name=object_name)

    def set_error(self, error_message, http_status = 400, return_value=None):
        self.result = False
        self.error_message = error_message
        self.http_status = http_status
        return return_value

    def pop_field(self,field, f_dict=None, default=None):
        if f_dict is None:
            f_dict = self.checked_parameters
        return f_dict.pop(field) if f_dict and field in f_dict else default

    def data_validate(self, f_required, f_optional):
        _fd = self.fields_defination
        ### To do the required test first.
        for field in f_required:
            if field not in self.parameters:
                return self.set_error("ERROR: Field '{}' is required.".format(field),return_value=False)

        ### To check value of each parameter for an operator, set boolen params in f_optional with field default value.
        self.checked_parameters = {f:_fd[f].default for f in filter(lambda f: isinstance(_fd[f],BoolType), f_optional)}
        for field in filter(lambda f: f in self.parameters, f_required + f_optional):
            checked_value = _fd[field].check(self.parameters[field])
            if checked_value is None:
                return self.set_error("ERROR: field '{}' get illegal value: '{}'".format(field,self.parameters[field]), return_value=False)
            self.checked_parameters[field] = checked_value
        return True

    def _check_obj_exists(self, obj_model, check_true=True):
        """
        This method should always run after method 'data_validate(...)'.
        """
        self.obj = self.get_object(obj_model, self.checked_parameters['name'])
        if check_true and self.obj is None:
            return self.set_error("ERROR: No {} object found with name: {}".format(obj_model.__name__, self.parameters['name']), return_value=False)
        if not check_true and self.obj is not None:   # For add method.
            return self.set_error("ERROR: {} object already existed with name: {}".format(obj_model.__name__, self.parameters['name']), return_value=False)
        return True

    def _get_queryset(self, obj_model):
        """
        For method 'show(...)' and 'showBind(...)'.
        This method should always run after method 'data_validate(...)'.
        """
        ### query.
        _chp = self.checked_parameters
        if 'name' in self.parameters:
            queryset = obj_model.objects.filter(name = _chp['name'])
            if not queryset.exists():
                return self.set_error("ERROR: {} object not exist with 'name: {}'.".format(obj_model.__name__, _chp['name']))
        else:
            queryset = obj_model.objects.all()
        return queryset

    def _data_show(self, queryset, instance=False):
        """
        This method should always run after method 'data_validate(...)'.
        Boolean parameter 'instance' is only used to show Modules.
        """
        if instance:
            _data = []
            for obj in queryset:
                if self.checked_parameters['--short']:
                    _data.append({'name':obj.name})
                else:
                    _attrs = obj.attrs
                    _attrs['instances'] = [i.name for i in obj.instances.all()]
                    _data.append(_attrs)
            return _data
        else:
            return list(map(lambda obj: {'name':obj.name} if self.checked_parameters['--short'] else obj.attrs, queryset))
