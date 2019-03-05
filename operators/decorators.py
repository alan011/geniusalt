from functools import wraps

def fields_validator(f_required, f_optional, check_obj_exists=True, obj_model=None, check_true=True):
    """
    This decorator is to validate 'self.parameters' for action methods of Operaters.
    If no error, self.check_parameters will set with meaningful values.

    'f_required' is list, which contains field names must be provided.
    'f_optional' is list, which contains field names can be provided optionally.
    'check_obj_exists' is a boolen. If True, logics of checking whether the object identify by field 'name' exist or not will be triggered. If no error, self.obj will be set.
    'obj_model' is a data model to check the object, which contains a field named 'name'. It will not work if check_obj_exists is False.
    'check_true' is a boolen. If True, object not exist will make an error_message. If False, object's existence will make an error_message.
    """
    def decorator(operator_action):
        @wraps(operator_action)
        def validate(self,*args,**kwargs):
            ### To validate API parameters.
            if not self.data_validate(f_required, f_optional): return

            ### if required, To check object's existence.
            if check_obj_exists and not self._check_obj_exists(obj_model=obj_model, check_true=check_true): return

            ### main work.
            return operator_action(self,*args,**kwargs)
        return validate
    return decorator
