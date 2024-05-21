import json
import logging
from collections import namedtuple

from django.apps import apps
from django.http.response import JsonResponse

from nets_core.params import RequestParam
from nets_core.responses import permission_denied
from django.utils.translation import gettext_lazy as _
from django.conf import settings

logger = logging.getLogger(__name__)

def get_project_from_db(project_id):
    if not hasattr(settings, 'NETS_CORE_PROJECT_MODEL'):
        raise ValueError(_("NETS_CORE_PROJECT_MODEL not found in settings"))
    
    try:
        model = apps.get_model(settings.NETS_CORE_PROJECT_MODEL)
        project = model.objects.get(id=project_id)
        return project
    except model.DoesNotExist:
        return None
    
def get_project_membership_from_db(project_id, user):
    if not hasattr(settings, 'NETS_CORE_PROJECT_MEMBER_MODEL'):
        raise ValueError(_("NETS_CORE_PROJECT_MEMBER_MODEL not found in settings"))
    
    try:
        model = apps.get_model(settings.NETS_CORE_PROJECT_MEMBER_MODEL)
        membership = model.objects.get(project_id=project_id, user=user)
        return membership
    except model.DoesNotExist:
        return None

def get_value_from_data_key(data, key, params, project, files):
    # Get value from data calling parse_param
    # to validate type and validate if is required
    # additional add customer to RequestParam instances
    # to ensure validation
    
    try:
        value = data[key]
        if not key in params.keys():
            return value
    except KeyError:
        pass
    
    param_type = params[key]
    if isinstance(param_type, RequestParam):
        if project:
            # Append project to parameter to validate
            # is required by RequestParam
            param_type.project = project
        if param_type.type == 'file':
            
            return param_type.get_file(files)
        
        return param_type.get_value(data)
        
    value = parse_param(data, [key, param_type])
    return value   

def parse_param(data, k):

    if isinstance(k, str):
        d = data.get(k, None)
        return d

    elif isinstance(k, list):
        data_key = k[0]
        data_type = k[1]

        if not isinstance(data_type, RequestParam):
            # build RequestParam object
            data_type  = RequestParam(data_key, data_type)
        
        # Exceptions handle by request_params_handler
        value = data_type.get_value(data)
        if not value and data_type.optional:
            print("returning default", data_type.default)
            return None
            
        return data_type.get_value(data)



def extract_data(request):
    
    if request.method == 'GET':
        return request.GET

    data = request.POST

    content_type = request.META.get(
        'CONTENT_TYPE', 'application/x-www-form-urlencoded')
    
    if content_type.startswith('application/json'):
        data = json.loads(request.body)

    return data

def request_params_handler(request, params: dict|list={}):
    data = extract_data(request)

    if request.user.is_anonymous and not request.public:
        return permission_denied()
    # TODO: Add support for multi customer projects
    project = None
    project_membership = None
    project_id = data.get('project_id', None)
    if project_id:
        project = get_project_from_db(data['project_id'])
        project_membership = get_project_membership_from_db(project_id, request.user)
    if request.project_required and not project:
        return JsonResponse({"res": 0, "message": "project_id is required"}, status=400)
    
    request.project = project
    request.project_id = project_id
    request.project_membership = project_membership
    
    parsed_data = {}
    # found_params = []

    for k in data:
        # parse data from request
        try:
            parsed_data[k] = get_value_from_data_key(data, k, params, request.project, request.FILES)
        except Exception as e:
            # Error parsing values
            msg = e.__str__()
            return JsonResponse({"res": 0, "message": msg}, status=400)
    
    # extract files
    for k in request.FILES:
        if k in params.keys():
            parsed_data[k] = get_value_from_data_key(data, k, params, request.project, request.FILES)

    if 'action' in parsed_data.keys():
        if not 'paginated_by' in parsed_data.keys():
            parsed_data['paginated_by'] = 25
        if not 'page'in parsed_data.keys():
            parsed_data["page"] = 1

    missing_params = []
    
    for p in params:
        optional = False
        if isinstance(params[p], RequestParam):
            optional = params[p].optional
            default = params[p].default if hasattr(params[p], 'default') else None
            if not p in parsed_data.keys() and optional:
                parsed_data[p] = default

        if p not in parsed_data.keys() and not optional:
            # Omit missing if is instance of RequestParams
            # because this class check and validate if self
            missing_params.append(p)

    if missing_params:
        message = "Missing params: {}".format(", ".join(missing_params))
        return JsonResponse({"res": 0, "message": message}, status=400)

    request.parsed_data = namedtuple(
        "Data", parsed_data.keys())(*parsed_data.values())
    # Keep compatibility with old code
    request.parse_data = request.parsed_data
    request.params = request.parsed_data
    return request


def get_request_obj(request, obj):
    """
        Get object from db using index_field
        and append to request object
        
        if obj has customer field, append customer
        attribute to request

        if obj has owner or user field, append
        is_owner and has_owner attributes to request.
        
        if not perm(public object or permission granted) and
        has_owner and not is_owner, return 404 

    """
    index_field = request.index_field
    try:
        o_query = {}
        if not hasattr(request.parsed_data, index_field):
            return JsonResponse({"res": 0, "message": _("index_field doesn't sent a valid value")})
        
        index_value = getattr(request.parsed_data, index_field, None)
        if not index_value:
            return JsonResponse({"res": 0, "message": _("index_field doesn't sent a valid value")})
        
        if isinstance(index_value, dict):
            index_value = index_value['value']

        o_query[index_field] = index_value
            
        if hasattr(obj, 'customer'):
            o_query['customer'] = request.customer
        
        o = obj.objects.get(**o_query)
        request.obj = o
        request.is_owner = False
        request.has_owner = False
        if hasattr(o, 'owner'):
            request.is_owner = o.owner == request.user
            request.has_owner = True

        if hasattr(o, 'user'):
            request.is_owner = o.user == request.user
            request.has_owner = True
            
        if not request.public:
            if not request.perm and (request.has_owner and not request.is_owner):
                logger.warning(f"User {request.user.id} tried to access {request.obj} {request.obj.id} without permission")
                return JsonResponse({"res": 0, "message": _("not found")}, status=404)
            
        request.obj = o
        return request
    except obj.DoesNotExist:
        return JsonResponse({"res": 0, "message": _("not found")}, status=404)