from channels.auth import AuthMiddlewareStack, UserLazyObject
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from oauth2_provider.models import AccessToken




@database_sync_to_async
def get_user(scope):
    """
    Return the user model instance associated with the given scope.
    If no user is retrieved, return an instance of `AnonymousUser`.
    """
    headers = dict(scope['headers'])
    user = None
    if b'authorization' in headers:

        access_token = headers[b'authorization'].decode()
        access_token = access_token.replace('Bearer ', '')

        try:
            token = AccessToken.objects.get(token=access_token)

            if token.is_valid():

                user = token.user
                # return user
            else:
                "received invalid token, delete from database"

                token.delete()
        except AccessToken.DoesNotExist:
            "token does not exist.... should be block future requests with invalid tokens?"
            pass
    u = user or AnonymousUser()

    return u


class AuthTokenMiddleware(BaseMiddleware):
    """
    Token authorization middleware for Django Channels 
    And OAUTH2 PROVIDER
    """
    
    def __init__(self, app):
        self.app = app

    def populate_scope(self, scope):
        if "user" not in scope:
            scope["user"] = UserLazyObject()

    async def resolve_scope(self, scope):
        if "user" not in scope or scope['user'] == AnonymousUser():
            scope["user"]._wrapped = await get_user(scope)

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        # Scope injection/mutation per this middleware's needs.
        self.populate_scope(scope)
        # Grab the finalized/resolved scope
        await self.resolve_scope(scope)

        return await self.app(scope, receive, send)
        # return await super().__call__(scope, receive, send)


def AuthTokenMiddlewareStack(inner): return (
    AuthMiddlewareStack(AuthTokenMiddleware(inner)))
