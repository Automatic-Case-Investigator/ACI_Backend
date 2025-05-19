from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.utils import IntegrityError
from rest_framework.views import APIView
from rest_framework import status

# API endpoint for handling username / password resets
class ResetCredentialsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        old_password = request.POST.get("old_password")
        new_username = request.POST.get("new_username")
        new_password = request.POST.get("new_password")

        if not old_password:
            return Response(
                {"error": "Old password is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not new_username or not new_password:
            return Response(
                {"error": "New username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not request.user.check_password(old_password):
            return Response(
                {"error": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            request.user.username = new_username
            request.user.set_password(new_password)
            request.user.save()
        
            refresh = RefreshToken.for_user(request.user)

            return Response(
                {
                    "message": "Success",
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                status=status.HTTP_200_OK,
            )
        except IntegrityError:
            return Response(
                {"error": "Username already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
