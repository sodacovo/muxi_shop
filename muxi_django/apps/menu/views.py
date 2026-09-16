import json

from django.shortcuts import render
from django.views import View
from django.http import HttpResponse, JsonResponse

from menu.models import MainMenu, SubMenu
from utils import ResponseMessage


# Create your views here.
class GoodsMainMenu(View):
    def get(self, request):
        print("get请求")
        main_menu = MainMenu.objects.all()
        result_list = []
        result_json = {}
        for m in main_menu:
            # result_list.append(m) # 隐式调用
            result_list.append(m.__str__()) # 显示调用
        # {status:1000,data:result_list}
        return ResponseMessage.MenuResponse.success(result_list)
        # result_json["status"] = 1000
        # result_json["data"] = result_list
        #
        # return HttpResponse(json.dumps(result_json),content_type="application/json")

class GoodsSubMenu(View):
    def get(self, request):
        # 获取请求的参数
        param_id = request.GET["main_menu_id"]
        # 拿到二级菜单的内容
        sub_menu = SubMenu.objects.filter(main_menu_id=param_id)
        result_list = []
        result_json = {}
        for m in sub_menu:
            # result_list.append(m) # 隐式调用
            result_list.append(m.__str__())  # 显示调用
        # {status:1000,data:result_list}
        # result_json["status"] = 1000
        # result_json["data"] = result_list
        return ResponseMessage.MenuResponse.success(result_list)
        # return HttpResponse(json.dumps(result_json), content_type="application/json")
