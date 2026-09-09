"""
Custom Django REST Framework Authentication class for Supabase Auth.

Verifies Supabase JWT access tokens using either:
1. Asymmetric JWKS (RS256/ES256) via Supabase's .well-known/jwks.json endpoint
2. Symmetric JWT Secret (HS256) via settings.SUPABASE_JWT_SECRET

Also supports signed Capacity Connect Django tokens for local admin/password login.
"""

import logging
import uuid
import jwt
from django.conf import settings
from django.core import signing
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import Role, UserProfile

logger = logging.getLogger(__name__)

_jwks_client = None

ALLOWED_ALGORITHMS = {'RS256', 'ES256', 'HS256'}


def get_jwks_client():
    """Returns a cached PyJWKClient instance for the configured Supabase URL."""
    global _jwks_client
    supabase_url = getattr(settings, 'SUPABASE_URL', None)
    if supabase_url and _jwks_client is None:
        jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_client = jwt.PyJWKClient(jwks_url)
    return _jwks_client


class SupabaseAuthentication(BaseAuthentication):
    """DRF authentication for Supabase JWTs and Capacity Connect Django tokens."""

    keyword = 'Bearer'

    def authenticate(self, request):
        auth_header = get_authorization_header(request).split()

        if not auth_header:
            return None

        if auth_header[0].decode().lower() != self.keyword.lower():
            return None

        if len(auth_header) == 1:
            raise AuthenticationFailed('Invalid token header. No credentials provided.')
        if len(auth_header) > 2:
            raise AuthenticationFailed('Invalid token header. Token string should not contain spaces.')

        token = auth_header[1].decode()
        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token: str):
        """Authenticate either a Capacity Connect token or a Supabase JWT."""
        if token.startswith('cc1.'):
            return self.authenticate_django_token(token)

        payload = self.decode_and_verify_token(token)
        user = self.get_or_create_user(payload)
        return (user, token)

    def authenticate_django_token(self, token: str):
        """Authenticate a Django user using a signed Capacity Connect token."""
        try:
            signed_token = token.removeprefix('cc1.')
            payload = signing.loads(
                signed_token,
                salt='capacity-connect-auth',
                max_age=60 * 60 * 24 * 7,
            )
            user_id = payload.get('user_id')
            if not user_id:
                raise AuthenticationFailed('Invalid authentication token.')

            user = User.objects.filter(id=user_id, is_active=True).first()
            if not user:
                raise AuthenticationFailed('User not found or inactive.')

            return (user, token)
        except signing.SignatureExpired:
            raise AuthenticationFailed('Authentication token has expired.')
        except signing.BadSignature:
            raise AuthenticationFailed('Invalid authentication token.')

    def decode_and_verify_token(self, token: str) -> dict:
        """Cryptographically decode and validate a Supabase JWT."""
        try:
            unverified_header = jwt.get_unverified_header(token)
            alg = unverified_header.get('alg')
        except Exception as e:
            raise AuthenticationFailed(f'Invalid token header format: {str(e)}')

        if not alg or alg not in ALLOWED_ALGORITHMS:
            raise AuthenticationFailed(f'Unsupported token algorithm: {alg}')

        jwt_secret = getattr(settings, 'SUPABASE_JWT_SECRET', None)
        supabase_url = getattr(settings, 'SUPABASE_URL', None)

        decode_kwargs = {
            'algorithms': [alg],
            'audience': 'authenticated',
            'options': {
                'verify_signature': True,
                'verify_exp': True,
                'verify_aud': True,
            },
        }

        if supabase_url:
            expected_issuer = f"{supabase_url.rstrip('/')}/auth/v1"
            decode_kwargs['issuer'] = expected_issuer
            decode_kwargs['options']['verify_iss'] = True

        if alg in ['RS256', 'ES256']:
            if not supabase_url:
                raise AuthenticationFailed('JWKS verification failed: SUPABASE_URL is not configured.')
            try:
                client = get_jwks_client()
                if not client:
                    raise AuthenticationFailed('JWKS client is not initialized.')
                signing_key = client.get_signing_key_from_jwt(token)
                return jwt.decode(token, signing_key.key, **decode_kwargs)
            except jwt.ExpiredSignatureError:
                raise AuthenticationFailed('Token has expired.')
            except jwt.InvalidAudienceError:
                raise AuthenticationFailed('Invalid token audience.')
            except jwt.InvalidIssuerError:
                raise AuthenticationFailed('Invalid token issuer.')
            except jwt.InvalidSignatureError:
                raise AuthenticationFailed('Invalid token signature.')
            except (jwt.PyJWKClientError, jwt.PyJWKError) as e:
                raise AuthenticationFailed(f'JWKS key retrieval failed: {str(e)}')
            except jwt.InvalidTokenError as e:
                raise AuthenticationFailed(f'Invalid token: {str(e)}')
            except Exception as e:
                raise AuthenticationFailed(f'Asymmetric token verification failed: {str(e)}')

        if alg == 'HS256':
            if not jwt_secret:
                raise AuthenticationFailed(
                    'Supabase authentication is not configured on the server. Missing SUPABASE_JWT_SECRET.'
                )
            try:
                return jwt.decode(token, jwt_secret, **decode_kwargs)
            except jwt.ExpiredSignatureError:
                raise AuthenticationFailed('Token has expired.')
            except jwt.InvalidAudienceError:
                raise AuthenticationFailed('Invalid token audience.')
            except jwt.InvalidIssuerError:
                raise AuthenticationFailed('Invalid token issuer.')
            except jwt.InvalidSignatureError:
                raise AuthenticationFailed('Invalid token signature.')
            except jwt.InvalidTokenError as e:
                raise AuthenticationFailed(f'Invalid token: {str(e)}')
            except Exception as e:
                raise AuthenticationFailed(f'Token verification failed: {str(e)}')

        raise AuthenticationFailed(f'Unhandled token algorithm: {alg}')

    def get_or_create_user(self, payload: dict) -> User:
        """Resolve or auto-provision a Django user from a verified Supabase token."""
        sub = payload.get('sub')
        if not sub:
            raise AuthenticationFailed('Token payload missing subject identifier (sub).')

        try:
            supabase_uuid = uuid.UUID(str(sub))
        except (ValueError, AttributeError):
            raise AuthenticationFailed('Invalid Supabase user UUID format.')

        profile = UserProfile.objects.filter(supabase_uid=supabase_uuid).select_related('user').first()
        if profile and profile.user:
            return profile.user

        email = payload.get('email', '').strip()
        user_metadata = payload.get('user_metadata', {}) or {}

        raw_role = str(user_metadata.get('role', '')).upper()
        if raw_role == Role.TRAINER:
            assigned_role = Role.TRAINER
        elif raw_role == Role.TRAINEE:
            assigned_role = Role.TRAINEE
        else:
            assigned_role = Role.TRAINEE

        raw_username = user_metadata.get('username') or (
            email.split('@')[0] if email else f'user_{str(supabase_uuid)[:8]}'
        )
        username = raw_username.strip()

        if User.objects.filter(username=username).exists():
            username = f"{username}_{str(supabase_uuid)[:4]}"
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{raw_username}_{str(supabase_uuid)[:4]}_{counter}"
                counter += 1

        user = User(username=username, email=email)
        user.set_unusable_password()
        user.save()

        UserProfile.objects.create(
            user=user,
            role=assigned_role,
            supabase_uid=supabase_uuid,
        )

        logger.info(
            f"Auto-provisioned new {assigned_role} user '{username}' "
            f"(Supabase UID: {supabase_uuid})"
        )
        return user

    def authenticate_header(self, request):
        return self.keyword
