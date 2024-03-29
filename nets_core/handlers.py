import json
from collections import namedtuple

from django.http.response import JsonResponse

from nets_core.params import RequestParam
from nets_core.responses import permission_denied
from django.utils.translation import gettext_lazy as _


def get_value_from_data_key(data, key, params, customer, files):
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
        if customer:
            # Append customer to parameter to validate
            # is required by RequestParam
            param_type.customer = customer
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
    customer = None
    # customer_id = data.get('customer_id', None)
    # if customer_id:
    #     customer = get_customer_from_db(data['customer_id'])
    # if request.customer_required and not customer:
    #     return JsonResponse({"res": 0, "message": "customer_id is required"}, status=400)
        
    # params_keys = params.keys()
    # request.customer = customer
    parsed_data = {}
    # found_params = []

    for k in data:
        # parse data from request
        try:
            parsed_data[k] = get_value_from_data_key(data, k, params, customer, request.FILES)
        except Exception as e:
            # Error parsing values
            msg = e.__str__()
            return JsonResponse({"res": 0, "message": msg}, status=400)
    
    # extract files
    for k in request.FILES:
        if k in params.keys():
            parsed_data[k] = get_value_from_data_key(data, k, params, customer, request.FILES)

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
            
        if not request.public:
            if not request.perm and (request.has_owner and not request.is_owner):
                return JsonResponse({"res": 0, "message": _("not found")}, status=404)
            
        request.obj = o
        return request
    except obj.DoesNotExist:
        return JsonResponse({"res": 0, "message": _("not found")}, status=404)