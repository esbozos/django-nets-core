from functools import wraps
import logging

from django.apps import apps
from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from nets_core.handlers import get_request_obj, request_params_handler
from nets_core.params import RequestParam
from nets_core.responses import permission_denied
from nets_core.utils import get_client_ip, check_perm



logger = logging.getLogger(__name__)

def request_handler(
    obj=None, 
    can_do: str=None, 
    perm_required: bool=False, 
    params: dict|list[RequestParam]={}, 
    optionals: dict={}, 
    allow_anonymous=False, 
    public=False,
    project_required=False,
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
            
            request.project = None
            request.project_membership = None
            
            # if project_required:
            #     if not hasattr(settings, 'NETS_CORE_PROJECT_MODEL'):
            #         raise Exception('NETS_CORE_PROJECT_MODEL not set in settings')
            #     else:
            #         if not hasattr(request, 'project_id'):
            #             return JsonResponse({"res": 0, "message": _('project_id required')}, status=400)
                    
            #         project_model = apps.get_model(settings.NETS_CORE_PROJECT_MODEL)
            #         try:
            #             project = project_model.objects.get(id=request.project_id)
            #             request.project = project
            #         except project_model.DoesNotExist:
            #             return JsonResponse({"res": 0, "message": _('project not found')}, status=404)
                    
            #     if not hasattr(settings, 'NETS_CORE_PROJECT_MEMBER_MODEL'):
            #         raise Exception('NETS_CORE_PROJECT_MEMBER_MODEL not set in settings')
            #     else:
            #         project_member_model = apps.get_model(settings.NETS_CORE_PROJECT_MEMBER_MODEL)
            #         try:
            #             project_member = project_member_model.objects.get(user=request.user, project=project)
            #             request.project_membership = project_member
            #         except project_member_model.DoesNotExist:
            #             if perm_required:
            #                 return JsonResponse({"res": 0, "message": _('project member not found')}, status=404)
                        
            
                
            request.project_required = project_required
            request.public = public
            request.index_field = index_field
            request = request_params_handler(request, _params)
            if isinstance(request, JsonResponse):
                return request
            
            perm = public
            if can_do:
                # TODO: log permission check
                perm = check_perm(request.user, can_do, request.project)              
                
                # log_permission_check.delay(request.user.id, can_do, access=perm, customer_id=customer_id)

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