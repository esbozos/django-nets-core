from functools import wraps
import logging

from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from nets_core.handlers import get_request_obj, request_params_handler
from nets_core.params import RequestParam
from nets_core.responses import permission_denied
from nets_core.utils import get_client_ip
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)

def request_handler(
    obj=None, 
    can_do: list=None, 
    perm_required: bool=False, 
    params: dict|list[RequestParam]={}, 
    optionals: dict={}, 
    allow_anonymous=False, 
    public=False,
    customer_required=False,
    index_field: str = 'id'):
    """
        Decorator for request params handler
        check if customer is required, permissions and obj
        append required attributes to request object
        
        obj: model class
        can_do: list of permissions to check
        pem_required: if True, check if user has permission
        params: list of RequestParam objects
        optionals: dict of optional params
        allow_anonymous: if True, allow anonymous users
        public: if True, allow public users
        customer_required: if True, check if customer_id is present in request
            and retrieve customer from db append to request object
        index_field: field to use as index for obj
    """

    def decorator(view_func):
        @csrf_exempt
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            
            if request.user.is_anonymous and not public:
                return permission_denied()
            
            _params = params

            if isinstance(_params, list):
                # check if params are list of RequestParam
                # and convert to dict
                _params_dict = {}
                for p in _params:
                    _params_dict[p.key] = p
                _params = _params_dict
                
            request.customer_required = customer_required
            request.public = public
            request.index_field = index_field
            request = request_params_handler(request, _params)
            if isinstance(request, JsonResponse):
                return request
            
            perm = public
            if can_do:
                # TODO: check_perm function
                perm = True
                # perm = check_perm(request.user, can_do[0], can_do[1], request.customer)
                customer_id = request.customer.id if request.customer else None
                # log_permission_check.delay(request.user.id, can_do[0], can_do[1], access=perm, customer_id=customer_id)

            if not perm and perm_required:
                return JsonResponse({"res": 0, "message": _('permission denied')}, status=403)
            
            request.perm = perm
            request.can_do = perm
            if obj:
                request = get_request_obj(request, obj)
                
                if isinstance(request, JsonResponse):
                    return request

            request.ip = get_client_ip(request)
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    return decorator