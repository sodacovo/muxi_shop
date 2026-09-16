import json
from base64 import encodebytes, decodebytes
from datetime import datetime
from urllib.parse import quote_plus

from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from django.conf import settings
from Crypto.PublicKey import RSA


class AliPay(object):
    def __init__(self):
        self.appid = settings.APPID
        self.app_notify_url = settings.APP_NOTIFY_URL  # 修复拼写错误（原aap_notify_url）
        self.return_url = settings.RETURN_URL
        self.debug = settings.ALIPAY_DEBUG
        self.app_private_key_path = settings.PRIVATE_KEY_PATH
        self.ali_pub_key_path = settings.ALI_PUB_KEY_PATH
        self.app_private_key = None
        self.ali_pub_key = None

        # 1. 读取并加载私钥（修复：确保路径正确，文件存在）
        try:
            with open(self.app_private_key_path, 'r', encoding='utf-8') as fp:
                self.app_private_key = RSA.importKey(fp.read())
        except Exception as e:
            raise ValueError(f"读取私钥失败：{str(e)}（请检查PRIVATE_KEY_PATH配置和文件格式）")

        # 2. 读取并加载支付宝公钥
        try:
            with open(self.ali_pub_key_path, 'r', encoding='utf-8') as fp:
                self.ali_pub_key = RSA.importKey(fp.read())
        except Exception as e:
            raise ValueError(f"读取支付宝公钥失败：{str(e)}（请检查ALI_PUB_KEY_PATH配置和文件格式）")

        # 3. 配置网关地址（修复沙箱地址，原地址少了dev）
        if self.debug:
            self.gateway = 'https://openapi-sandbox.dl.alipaydev.com/gateway.do'  # 正确沙箱地址
        else:
            self.gateway = 'https://openapi.alipay.com/gateway.do'  # 正式环境地址

    # -------------------------- 以下方法移出__init__，作为类的实例方法 --------------------------
    def direct_pay(self, subject, out_trade_no, total_amount, **kwargs):
        """创建电脑网站支付链接"""
        biz_content = {
            "subject": subject,
            "out_trade_no": out_trade_no,
            "total_amount": str(total_amount),  # 关键：支付宝要求金额为字符串，避免小数精度问题
            "product_code": "FAST_INSTANT_TRADE_PAY",
        }
        biz_content.update(kwargs)
        data = self.build_body("alipay.trade.page.pay", biz_content, self.return_url)
        return self.sign_data(data)

    def build_body(self, method, biz_content, return_url=None):
        """构建支付宝请求公共参数"""
        # 确保biz_content是字符串（如果是字典则转为JSON）
        if isinstance(biz_content, dict):
            biz_content = json.dumps(biz_content, separators=(',', ':'), ensure_ascii=False)

        data = {
            "app_id": self.appid,
            "method": method,
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "biz_content": biz_content
        }

        if return_url is not None:
            data["notify_url"] = self.app_notify_url
            data["return_url"] = self.return_url

        return data

    def sign_data(self, data):
        """对请求参数进行RSA2签名"""
        # 移除可能存在的sign参数
        data.pop("sign", None)
        # 按支付宝要求对参数排序
        unsigned_items = self.order_data(data)
        # 拼接未签名字符串
        unsigned_string = "&".join(f"{k}={v}" for k, v in unsigned_items)
        # 签名
        signer = PKCS1_v1_5.new(self.app_private_key)
        signature = signer.sign(SHA256.new(unsigned_string.encode("utf-8")))
        # 对签名结果进行base64编码并去除换行
        sign = encodebytes(signature).decode("utf8").replace("\n", "")
        # 对参数和签名进行URL编码
        quoted_string = "&".join(f"{k}={quote_plus(v)}" for k, v in unsigned_items)
        # 返回最终的带签名的请求字符串
        return quoted_string + "&sign=" + quote_plus(sign)

    def order_data(self, data):
        """对参数按key进行ASCII排序（支付宝要求）"""
        # 处理嵌套字典（转为JSON字符串）
        complex_keys = [k for k, v in data.items() if isinstance(v, dict)]
        for key in complex_keys:
            data[key] = json.dumps(data[key], separators=(',', ':'), ensure_ascii=False)
        # 按key排序并返回列表
        return sorted(data.items(), key=lambda x: x[0])

    def _verify(self, raw_content, signature):
        """验证签名核心逻辑"""
        verifier = PKCS1_v1_5.new(self.ali_pub_key)
        digest = SHA256.new(raw_content.encode("utf-8"))
        return verifier.verify(digest, decodebytes(signature.encode("utf-8")))

    def verify(self, data, signature):
        """验证支付宝回调参数的签名"""
        if "sign_type" in data:
            data.pop("sign_type")  # 移除sign_type，不参与签名验证
        # 排序参数并拼接
        unsigned_items = self.order_data(data)
        raw_content = "&".join(f"{k}={v}" for k, v in unsigned_items)
        # 验证签名
        return self._verify(raw_content, signature)