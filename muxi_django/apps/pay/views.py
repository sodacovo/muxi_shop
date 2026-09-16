import qrcode
import hashlib
from io import BytesIO
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from rest_framework.views import APIView
from datetime import datetime
from rest_framework.permissions import AllowAny
from order.models import Order, OrderGoods
from pay.alipay import AliPay



# Create your views here.
class ToAliPayPageAPIView(APIView):
    def post(self, request):
        # 日志1：打印前端传递的原始请求数据，确认tradeNo和orderAmount是否传递到后端
        # print("=== 支付发起 - 前端请求数据 ===")
        # print("request.data:", request.data)  # 关键：看是否有"tradeNo"和"orderAmount"字段
        
        if not request.user.get("status"):
            # print("=== 支付发起 - 认证失败 ===")
            print("request.user:", request.user)  # 若认证失败，打印失败原因
            return JsonResponse(request.user, safe=False)
        
        # 日志2：打印提取的订单号和金额，确认参数是否正确获取
        trade_no = request.data.get("tradeNo")
        total_amount = request.data.get("orderAmount")
        # print("=== 支付发起 - 提取的参数 ===")
        # print("trade_no（订单号）:", trade_no)
        # print("total_amount（订单金额）:", total_amount)
        
        # 日志3：捕获Alipay初始化和链接生成的异常（防止密钥路径错误导致失败）
        try:
            alipay = AliPay()
            url = alipay.direct_pay(
                out_trade_no=trade_no,
                subject="主题:" + trade_no,
                total_amount=total_amount,
            )
            re_url = alipay.gateway + "?{data}".format(data=url)
            # 日志4：打印生成的支付宝支付链接，确认链接是否有效
            # print("=== 支付发起 - 生成支付宝链接 ===")
            # print("支付宝支付链接:", re_url)
            return JsonResponse({"alipay": re_url})
        except Exception as e:
            # print("=== 支付发起 - 生成链接失败 ===")
            print("错误原因:", str(e))  # 打印具体错误（如密钥文件找不到、参数格式错误）
            return JsonResponse({"status": 500, "error": "生成支付链接失败"}, safe=False)


class AlipayAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # 同步回调（支付宝支付完成后3秒跳转的回调）
        # 日志1：打印支付宝回调的所有参数，确认是否传递了out_trade_no、sign等关键字段
        # print("\n=== 同步回调 - 支付宝传递的参数 ===")
        # print("request.GET（回调参数）:", request.GET.dict())  # 转为字典，方便查看
        
        processed_dict = {}
        for k, v in request.GET.items():
            processed_dict[k] = v
        sign = processed_dict.pop("sign", None)
        
        # 日志2：打印提取的签名和处理后的参数，确认签名是否存在
        # print("=== 同步回调 - 签名处理 ===")
        # print("提取的sign（签名）:", sign)
        # print("处理后的参数（去除sign）:", processed_dict)
        
        # 日志3：捕获签名验证和订单更新的异常
        try:
            alipay = AliPay()
            is_verify = alipay.verify(processed_dict, sign)
            # 日志4：打印签名验证结果，确认是否验证通过（True=通过，False=失败）
            # print("=== 同步回调 - 签名验证结果 ===")
            # print("is_verify（签名是否通过）:", is_verify)
            
            if is_verify is True:
                trade_no = processed_dict.get('out_trade_no')  # 你的订单号
                ali_trade_no = processed_dict.get('trade_no')  # 支付宝的订单号
                # 日志5：打印回调的订单号，确认是否与数据库中的订单号匹配
                # print("=== 同步回调 - 订单信息 ===")
                # print("out_trade_no（你的订单号）:", trade_no)
                # print("ali_trade_no（支付宝订单号）:", ali_trade_no)
                
                # 日志6：打印订单更新前的状态，确认订单是否存在
                order_before = Order.objects.filter(trade_no=trade_no).first()
                # print("=== 同步回调 - 订单更新前状态 ===")
                # if order_before:
                    # print("订单当前pay_status:", order_before.pay_status)
                    # print("订单当前ali_trade_no:", order_before.ali_trade_no)
                # else:
                    # print("订单不存在！trade_no:", trade_no)  # 关键：排查订单是否存在
                
                # 更新订单状态
                update_count = Order.objects.filter(trade_no=trade_no).update(
                    ali_trade_no=ali_trade_no,
                    pay_status=2,  # 2=支付完成
                    pay_time=datetime.now()
                )
                # 日志7：打印订单更新结果，确认是否成功更新（update_count=1表示成功）
                # print("=== 同步回调 - 订单更新结果 ===")
                # print("更新影响的订单数量:", update_count)  # 1=成功，0=未找到订单
            
        except Exception as e:
            # print("=== 同步回调 - 处理失败 ===")
            print("错误原因:", str(e))  # 打印异常（如密钥错误、订单模型字段错误）
        

        redirect_url = "https://www.nwq1309.shop/profile?activeIndex=3"  # 改为你的前端公网地址
        # print("=== 同步回调 - 最终跳转地址 ===")
        # print("跳转地址:", redirect_url)  # 验证是否已修改为正确的公网地址
        return redirect(redirect_url)

    def post(self, request):
        # 异步回调（支付宝后台主动通知的回调，用于确保订单状态最终一致）
        # 日志1：打印支付宝异步回调的所有参数
        # print("\n=== 异步回调 - 支付宝传递的参数 ===")
        # print("request.POST（回调参数）:", request.POST.dict())
        
        processed_dict = {}
        for k, v in request.POST.items():
            processed_dict[k] = v
        sign = processed_dict.pop("sign", None)
        
        # print("=== 异步回调 - 签名处理 ===")
        # print("提取的sign（签名）:", sign)
        # print("处理后的参数（去除sign）:", processed_dict)
        
        try:
            alipay = AliPay()
            is_verify = alipay.verify(processed_dict, sign)
            # print("=== 异步回调 - 签名验证结果 ===")
            # print("is_verify（签名是否通过）:", is_verify)
            
            if is_verify is True:
                # -------------------------- 新增：交易状态校验 --------------------------
                trade_status = processed_dict.get('trade_status')  # 获取支付宝交易状态
                # print("=== 异步回调 - 交易状态 ===")
                # print("trade_status（支付宝返回状态）:", trade_status)
                
                # 只有“支付成功”或“交易结束”的状态，才更新订单（避免非成功状态误更新）
                if trade_status not in ('TRADE_SUCCESS', 'TRADE_FINISHED'):
                    # print("=== 异步回调 - 非支付成功状态，不更新订单 ===")
                    return JsonResponse({"code": "success"}, safe=False)
                # ----------------------------------------------------------------------
                
                trade_no = processed_dict.get('out_trade_no')
                ali_trade_no = processed_dict.get('trade_no')
                # print("=== 异步回调 - 订单信息 ===")
                # print("out_trade_no（你的订单号）:", trade_no)
                # print("ali_trade_no（支付宝订单号）:", ali_trade_no)
                
                # 检查订单是否已更新（防止重复回调）
                order = Order.objects.filter(trade_no=trade_no).first()
                if order and order.pay_status == 2:
                    # print("=== 异步回调 - 订单已更新过 ===")
                    return JsonResponse({"code": "success", "msg": "订单已处理"}, safe=False)
                
                # 更新订单状态
                update_count = Order.objects.filter(trade_no=trade_no).update(
                    ali_trade_no=ali_trade_no,
                    pay_status=2,  # 2=支付完成
                    pay_time=datetime.now()
                )
                # print("=== 异步回调 - 订单更新结果 ===")
                # print("更新影响的订单数量:", update_count)
        
        except Exception as e:
            # print("=== 异步回调 - 处理失败 ===")
            print("错误原因:", str(e))
        
        # 支付宝要求异步回调必须返回"success"（小写），否则会重复发送通知
        return JsonResponse({"code": "success"}, safe=False)
        
        
# 1. 生成微信支付二维码（返回blob图片）
def wechat_pay_qrcode(request):
    trade_no = request.GET.get("trade_no", "").strip('/')
    if not trade_no:
        return HttpResponse("缺少订单号", status=400)
    try:
        # 查待支付订单（不变）
        order = Order.objects.get(
            trade_no=trade_no, 
            pay_status__in=["0", "1"],  # 兼容0和1，避免因状态错误导致功能失效
            is_delete=0  # 补充is_delete=0，确保只查未删除订单
        )
        total_amount = int(float(order.order_amount) * 100)
        order_goods = OrderGoods.objects.filter(trade_no=trade_no).first()
        # 2. 处理订单项和sku_id（容错：没有订单项/sku_id为空时用默认名）
        if order_goods and order_goods.sku_id:  # 有订单项且sku_id不为空
            goods_name = f"商品-{order_goods.sku_id}"  
        else:
            goods_name = "木犀商城商品"  # 无商品时用默认名
        
        # Mock微信统一下单、签名生成、二维码生成的代码
        params = {
            "appid": "wx1234567890abcdef",
            "mch_id": "1900009881",
            "nonce_str": "abcdef1234567890",
            "body": f"木犀商城-{goods_name}",  
            "out_trade_no": trade_no,
            "total_fee": total_amount,
            "spbill_create_ip": request.META.get("REMOTE_ADDR", "127.0.0.1"),
            "notify_url": settings.WECHAT_PAY_CONFIG["notify_url"],
            "trade_type": "NATIVE",
        }
        # 生成签名（不变）
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        sign_str = "&".join([f"{k}={v}" for k, v in sorted_params]) + f"&key={settings.WECHAT_PAY_CONFIG['api_key']}"
        params["sign"] = hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()
        
        # 生成二维码（不变）
        code_url = "weixin://wxpay/bizpayurl?pr=8Z7Zu00"
        img = qrcode.make(code_url)
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        
        return HttpResponse(buf.getvalue(), content_type="image/png")
    except Order.DoesNotExist:
        # 打印详细日志，方便后续排查
        # print(f"=== 微信二维码查询失败 ===")
        print(f"trade_no：{trade_no}")
        print(f"当前订单实际pay_status：{Order.objects.filter(trade_no=trade_no).first().pay_status if Order.objects.filter(trade_no=trade_no).exists() else '订单不存在'}")
        return HttpResponse("订单不存在或已支付", status=400)  # 改400，避免前端误解路径错误
    except Exception as e:
        # print(f"=== 生成二维码失败 ===")
        print(f"错误：{str(e)}")
        return HttpResponse(f"生成二维码失败：{str(e)}", status=500)

# 2. 查询微信支付状态（前端轮询调用）
def wechat_pay_query(request):
    trade_no = request.GET.get("trade_no", "").strip('/')
    if not trade_no:
        return JsonResponse({"status": "fail", "message": "缺少订单号"})
    try:
        order = Order.objects.get(trade_no=trade_no)
        # 模拟状态：订单为1表示支付成功（后续用Admin手动标记）
        if order.pay_status == "2":
            return JsonResponse({"status": "success", "message": "支付成功"})
        return JsonResponse({"status": "pending", "message": "待支付"})
    except Order.DoesNotExist:
        return JsonResponse({"status": "fail", "message": "订单不存在"})

# 3. 微信支付回调接口（Mock，演示幂等性）
def wechat_pay_notify(request):
    if request.method != "POST":
        return HttpResponse('<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[仅支持POST]]></return_msg></xml>')
    try:
        # 模拟解析微信回调XML（真实项目用xmltodict库）
        notify_data = {
            "out_trade_no": request.POST.get("out_trade_no", ""),
            "trade_state": "SUCCESS",
            "sign": request.POST.get("sign", "")
        }
        trade_no = notify_data["out_trade_no"]
        if not trade_no:
            return HttpResponse('<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[缺少订单号]]></return_msg></xml>')
        
        # 1. 幂等性处理（避免重复回调）
        order = Order.objects.get(trade_no=trade_no)
        if order.pay_status == "2":
            return HttpResponse('<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>')
        
        # 2. 改订单状态
        order.pay_status = "2"
        order.save()
        return HttpResponse('<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>')
    except Order.DoesNotExist:
        return HttpResponse('<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[订单不存在]]></return_msg></xml>')
    except Exception as e:
        return HttpResponse(f'<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[{str(e)}]]></return_msg></xml>')
        
        
def get_order_detail(request):
    """订单详情接口：返回订单金额、商品列表（供收银台渲染）"""
    trade_no = request.GET.get("tradeNo")  # 前端传的tradeNo
    if not trade_no:
        return JsonResponse({
            "status": "fail", 
            "message": "缺少订单号",
            "data": {}
        })
    
    try:
        # 1. 查询订单基本信息（金额、状态）
        order = Order.objects.get(
            trade_no=trade_no,
            pay_status="0",  # 只查待支付订单
            is_delete="0"    # 只查未删除订单
        )
        
        # 2. 查询该订单的商品列表（OrderGoods）
        goods_list = OrderGoods.objects.filter(trade_no=trade_no)
        
        # 3. 处理商品数据（格式给前端）
        goods_data = []
        for goods in goods_list:
            # 若有商品表（如Goods/Sku），可关联查真实名称/单价；没有则用默认值
            goods_data.append({
                "sku_id": goods.sku_id,
                "goods_name": f"木犀商品-{goods.sku_id}",  # 默认名称
                "goods_num": goods.goods_num,             # 数量
                "price": "0.00" if not order.order_amount else (float(order.order_amount)/len(goods_list))  # 简化：平均单价
            })
        
        # 4. 返回数据给前端（金额转字符串，避免Decimal类型问题）
        return JsonResponse({
            "status": "success",
            "message": "获取订单详情成功",
            "data": {
                "order_amount": str(order.order_amount),  # 金额（转字符串，前端显示正常）
                "trade_no": trade_no,
                "goods": goods_data  # 商品列表
            }
        })
    
    except Order.DoesNotExist:
        return JsonResponse({
            "status": "fail",
            "message": "订单不存在或已支付/删除",
            "data": {}
        })
    except Exception as e:
        return JsonResponse({
            "status": "fail",
            "message": f"获取订单详情失败：{str(e)}",
            "data": {}
        })