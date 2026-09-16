from ronglian_sms_sdk import SmsSDK
import json  # 新增：用于解析响应

accId = '2c94811c9787a27f01982aef45cb2192'
accToken = 'd3f8668e751c4021875cb4afa66d0d4e'
appId = '2c94811c9787a27f01982aef47962199'
templateId = '1'  # 确保该模板ID在容联云后台已审核通过


class SMS:
    @staticmethod
    def send_sms(phone, code):
        try:
            sdk = SmsSDK(accId, accToken, appId)
            datas = (code, '5')  # 验证码和有效期（5分钟）
            resp_str = sdk.sendMessage(templateId, phone, datas)  # 返回JSON字符串
            resp = json.loads(resp_str)  # 解析为字典

            # 容联云：statusCode为"000000"表示发送成功
            if resp.get('statusCode') == '000000':
                return True
            else:
                # 打印错误信息（便于调试）
                print(f"短信发送失败：{resp.get('statusCode')}，{resp.get('statusMsg')}")
                return False
        except Exception as e:
            print(f"短信发送异常：{str(e)}")
            return False