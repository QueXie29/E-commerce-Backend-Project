from rest_framework.response import Response


def api_response(data=None, message: str = "success", code: int = 0, status=None):
    return Response(
        {
            "code": code,
            "message": message,
            "data": data,
        },
        status=status,
    )
