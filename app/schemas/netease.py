from pydantic import BaseModel, Field


class NeteaseCaptchaRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=20, pattern=r"^\+?\d+$", description="手机号码")
    ctcode: str = Field("86", min_length=1, max_length=5, pattern=r"^\d+$", description="国家区号")


class NeteaseCellphoneLoginRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=20, pattern=r"^\+?\d+$", description="手机号码")
    captcha: str = Field(..., min_length=1, max_length=10, pattern=r"^\d+$", description="短信验证码")
    countrycode: str = Field("86", min_length=1, max_length=5, pattern=r"^\d+$", description="国家码")
