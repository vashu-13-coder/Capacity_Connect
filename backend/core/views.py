"""
Views for the core authentication module.

Provides Register, Login, Logout, and CurrentUser API views.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core import signing
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Role
from .permissions import IsAdmin
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    AdminUserListSerializer,
    AdminUserDetailSerializer,
)
from .throttling import AuthRateThrottle


class RegisterView(APIView):
    """Create a public Trainee or Trainer account."""
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    POST /api/auth/login/

    Authenticate a Django user and return a signed application token.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )

        if user is None:
            return Response(
                {'detail': 'Invalid username or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {'detail': 'This account is disabled.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        signed_token = signing.dumps(
            {'user_id': user.id},
            salt='capacity-connect-auth',
        )

        return Response({
            'token': f'cc1.{signed_token}',
            'user': UserSerializer(user).data,
        })


class LogoutView(APIView):
    """POST /api/auth/logout/."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({'detail': 'Successfully logged out.'})


class CurrentUserView(APIView):
    """GET /api/auth/me/."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class AdminUserListView(APIView):
    """GET /api/auth/admin/users/."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        users = User.objects.select_related('profile').all().order_by('-date_joined')

        role_filter = request.query_params.get('role')
        if role_filter:
            users = users.filter(profile__role=role_filter.upper())

        search = request.query_params.get('search')
        if search:
            users = users.filter(
                Q(username__icontains=search) | Q(email__icontains=search)
            )

        serializer = AdminUserListSerializer(users, many=True)
        return Response(serializer.data)


class AdminUserDetailView(APIView):
    """GET /api/auth/admin/users/<pk>/."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, pk):
        from django.shortcuts import get_object_or_404
        user = get_object_or_404(User, pk=pk)
        return Response(AdminUserDetailSerializer(user).data)


class AdminUserDeactivateView(APIView):
    """POST /api/auth/admin/users/<pk>/deactivate/."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        from django.shortcuts import get_object_or_404
        user = get_object_or_404(User, pk=pk)

        if user.pk == request.user.pk:
            return Response(
                {'detail': 'Cannot deactivate your own account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(user, 'profile') and user.profile.role == Role.ADMIN:
            return Response(
                {'detail': 'Cannot deactivate admin accounts.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {'detail': 'User is already inactive.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'detail': f'User "{user.username}" has been deactivated.'})


class AdminUserActivateView(APIView):
    """POST /api/auth/admin/users/<pk>/activate/."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        from django.shortcuts import get_object_or_404
        user = get_object_or_404(User, pk=pk)

        if user.is_active:
            return Response(
                {'detail': 'User is already active.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'detail': f'User "{user.username}" has been reactivated.'})
