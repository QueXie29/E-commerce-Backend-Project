from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class BusinessException(APIException):
    status_code = 400
    default_detail = "业务处理失败"
    default_code = "business_error"

    def __init__(
        self,
        message: str | None = None,
        code: int = 40000,
        data=None,
        status_code: int = 400,
    ):
        self.status_code = status_code
        super().__init__(detail=message or self.default_detail, code=self.default_code)
        self.business_code = code
        self.data = data


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    code = getattr(exc, "business_code", None)
    if code is None:
        code = {
            400: 40000,
            401: 40100,
            403: 40300,
            404: 40400,
        }.get(response.status_code, 50000)

    detail = response.data.get("detail") if isinstance(response.data, dict) else response.data
    if isinstance(detail, str):
        message = detail
        data = getattr(exc, "data", None)
    else:
        message = {
            400: "请求参数错误",
            401: "未认证",
            403: "无权限",
            404: "资源不存在",
        }.get(response.status_code, "服务器内部错误")
        data = response.data

    response.data = {
        "code": code,
        "message": message,
        "data": data,
    }
    return response
