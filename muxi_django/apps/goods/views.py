import decimal
import json
import logging
from datetime import datetime
from django.db import connection
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django_redis import get_redis_connection
from rest_framework.response import Response
from rest_framework.views import APIView
from sqlparse import sql
from prometheus_client import Gauge, CollectorRegistry, generate_latest
from goods.models import Goods
from goods.serializers import GoodsSerializer
from utils import ResponseMessage
from utils.ResponseMessage import SeckillResponse
from goods.utils import record_user_behavior

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from django.db.models import Count
from prometheus_client import REGISTRY
from django.views.decorators.csrf import csrf_exempt

# Create your views here.
# 获取商品分类的接口
# 访问方式 http://localhost:8000/goods/category/1
class GoodsCategoryAPIView(APIView):
    def get(self,request, category_id, page):
        current_page = (page-1)*20
        end_data = page * 20
        category_data = Goods.objects.filter(
            type_id=category_id
        ).all()[current_page:end_data]
        result_list = []
        # m.__str__()返回的是字符串，虽然字符串可以被 JSON 序列化
        for m in category_data:
            result_list.append(m.__str__())
        return ResponseMessage.GoodsResponse.success(result_list)

        # 使用序列化器处理查询集
        # serializer = GoodsSerializer(instance=category_data, many=True)
        # return ResponseMessage.GoodsResponse.success(serializer.data)


class GoodsDetailAPIView(APIView):
    def get(self, request, sku_id):
        # print(sku_id)
        goods_data = Goods.objects.filter(
            sku_id=sku_id
        ).first()
        if not goods_data:                      # 空商品 → 不弹框，给空壳
            # 控制台留痕，方便排查
            print(f"[WARN] sku_id={sku_id} 未找到商品，返回空壳数据")
            return ResponseMessage.GoodsResponse.failed("商品不存在")
        # 进行序列化的动作 序列化的参数时instance 反序列化的参数就是data
        result = GoodsSerializer(instance=goods_data)
        
        # 🔥 兼容处理：先判断是否是未登录用户，再处理登录用户的字典
        try:
            # 未登录（AnonymousUser）→ 不执行埋点
            if not isinstance(request.user, AnonymousUser):
                # 登录用户：判断是否是字典 + status是否有效
                if isinstance(request.user, dict) and request.user.get('status'):
                    user_id = request.user.get('data', {}).get('user_id')
                    if user_id:  # 兜底：确保user_id存在才埋点
                        record_user_behavior(user_id, goods_data.id)
        except Exception as e:
            logging.warning(f"商品详情埋点失败：{str(e)}")  # 容错，不影响接口返回
        
        return ResponseMessage.GoodsResponse.success(result.data)


class GoodsFindAPIView(APIView):
    def get(self, request):
        goods_data = Goods.objects.filter(find=1).all()
        result = GoodsSerializer(instance=goods_data, many=True)
        return ResponseMessage.GoodsResponse.success(result.data)


class GoodSearchAPIView(APIView):
    def get(self, request, keyword, page, order_by):
        # if not request.user.get('status'):
        #     return JsonResponse(request.user, safe=False)
        # 计算分页偏移量
        limit_page = (page - 1) * 10

        # 排序字段映射，增加默认值避免KeyError
        order_dict = {
            1: "r.comment_count",
            2: "g.p_price"
        }
        # 确保排序字段有效，默认为按评论数排序
        order_field = order_dict.get(order_by, "r.comment_count")

        # 修复SQL语法：
        # 1. concat函数缺少逗号
        # 2. like条件使用参数化避免SQL注入
        # 3. 调整字符串格式化方式
        sql = """
            select 
                r.comment_count,
                concat('{}', g.image) as image,
                g.name,
                g.p_price,
                g.shop_name,
                g.sku_id 
            from goods g
            left join (
                select 
                    count(c.sku_id) as comment_count,
                    c.sku_id 
                from comment c
                group by c.sku_id
            ) r on g.sku_id = r.sku_id
            where g.name like %s 
            order by {} desc 
            limit %s, 15
        """.format(settings.IMAGE_URL, order_field)

        try:
            cursor = connection.cursor()
            # 执行参数化查询，避免SQL注入
            cursor.execute(sql, [f"%{keyword}%", limit_page])
            res = self.dict_fetchall(cursor)

            # 正确处理JSON序列化
            final_list = []
            for item in res:
                # 直接序列化字典，无需先转JSON字符串
                final_list.append(json.dumps(item, cls=DecimalEncoder, ensure_ascii=False))

            return ResponseMessage.GoodsResponse.success(final_list)
        except Exception as e:
            # 捕获并返回错误信息，便于调试
            return Response({"error": str(e)}, status=500)
        finally:
            # 确保游标关闭
            if 'cursor' in locals():
                cursor.close()

    def dict_fetchall(self, cursor):
        # 修复列表推导式的语法错误
        desc = cursor.description
        '''
        （cursor）的 description 属性，存储了 “查询结果的字段信息”，
        是一个列表，每个元素对应一个字段的元组
        例如你查询的字段是 comment_count、image、name，那么 desc 的结构类似：
        [
    ('comment_count', ...),  # 第一个字段：字段名是 'comment_count'
    ('image', ...),          # 第二个字段：字段名是 'image'
    ('name', ...),           # 第三个字段：字段名是 'name'
    ...  # 其他字段（p_price、shop_name、sku_id）
]
        '''
        # 原代码中括号位置错误，导致生成器表达式不正确
        #核心作用是把数据库返回的 “无字段名的元组数据”，转换成 “键为字段名、值为数据的字典列表”，
        # 方便后续按字段名（如 name、price）读取数据。
        '''
           cursor.fetchall()从游标中获取 “所有查询结果行”，
           返回一个列表，每个元素是一个 “元组”，元组中的值对应 “每一行的字段数据”
           例如查询到两条商品数据，cursor.fetchall() 的结构类似：
           [
           (100, 'http://xxx.jpg', '苹果手机', 5999, '苹果旗舰店', 1001),  # 第一行数据
           (80, 'http://yyy.jpg', '华为手机', 4999, '华为旗舰店', 1002)    # 第二行数据
       ]
           '''
        return [dict(zip([col[0] for col in desc], row)) for row in cursor.fetchall()]
    """
        拆解列表推导式：3 步把 “元组” 转 “字典”
        第 1 步：提取 “纯字段名列表”——[col[0] for col in desc]
            col 是 desc 中的每个元素（如 ('comment_count', ...)）；
            col[0] 是取每个字段元组的 “第一个值”（即字段名，如 'comment_count'）
            作用是从 desc（字段信息列表）中，只提取 “每个字段的名称”，生成一个纯字段名列表。
            执行后得到：['comment_count', 'image', 'name', 'p_price', 'shop_name', 'sku_id']
        
        第 2 步：将 “字段名列表” 与 “单行数据元组” 配对 ——zip(字段名列表, row)
            row 是 cursor.fetchall() 中的每一行数据（如 (100, 'http://xxx.jpg', '苹果手机', ...)）；
            zip(a, b) 是 Python 内置函数，作用是 “将两个列表按索引一一配对”，返回一个迭代器，每个元素是配对的元组。
            执行后得到：zip(
                ['comment_count', 'image', 'name', ...],
                (100, 'http://xxx.jpg', '苹果手机', ...)
            )
            # 配对结果（迭代器展开后）：
            [('comment_count', 100), ('image', 'http://xxx.jpg'), ('name', '苹果手机'), ...]
        
        第 3 步：将 “配对元组” 转成字典 ——dict(zip(...))
            生成：{
                    'comment_count': 100,
                    'image': 'http://xxx.jpg',
                    'name': '苹果手机',
                    'p_price': 5999,
                    'shop_name': '苹果旗舰店',
                    'sku_id': 1001
                }
        第 4 步：遍历所有行，生成 “字典列表”—— 外层推导式            
    """



class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        elif isinstance(o, datetime):
            return o.strftime("%Y-%m-%d %H:%M:%S")
        # 调用父类处理其他类型
        return super(DecimalEncoder, self).default(o)

class GoodsSearchDataCountAPIView(APIView):
    '''
    接收前端搜索关键词，通过 django-elasticsearch-dsl 构建 ES 查询语句，从 ES 中高效查询数据并返回。
    '''
    def get(self, request, keyword):
        count = Goods.objects.filter(name__contains=keyword).count()
        return HttpResponse(count)


class InitSeckillStockAPIView(APIView):
    """
    秒杀库存初始化：将 Goods 表的 seckill_stock 同步到 seckill 缓存库（3号库）
    调用方式：POST /goods/init-seckill-stock/
    """
    def post(self, request):
        try:
            # 1. 连接Redis（捕获Redis连接异常）
            try:
                redis_conn = get_redis_connection('seckill')  # 指定秒杀缓存库
            except Exception as e:
                # Redis连接失败 → 返回8001（失败）
                return SeckillResponse.failed({
                    "message": "Redis连接失败",
                    "error": str(e)[:50]  # 只返回前50个字符，避免敏感信息
                })

            # 2. 查询数据库（未结束的秒杀商品）
            now = timezone.now()
            try:
                seckill_goods = Goods.objects.filter(
                    is_seckill=True,  # 是秒杀商品
                    seckill_end_time__gt=now  # 秒杀未结束
                )
            except Exception as e:
                # 数据库查询错误 → 返回8001（失败）
                return SeckillResponse.failed({
                    "message": "数据库查询秒杀商品失败",
                    "error": str(e)[:50]
                })

            # 3. 同步库存到Redis
            sync_count = 0
            for goods in seckill_goods:
                stock_key = f"seckill:stock:{goods.id}"
                redis_conn.set(stock_key, goods.seckill_stock)
                # 计算过期时间（秒杀结束后+1小时）
                expire_seconds = (goods.seckill_end_time - now).seconds + 3600
                redis_conn.expire(stock_key, expire_seconds)
                sync_count += 1

            # 4. 根据同步结果返回不同响应
            if sync_count >= 1:
                # 同步到商品 → 返回8000（成功）
                return SeckillResponse.success({
                    "message": f"秒杀库存初始化完成！同步{sync_count}个商品到Redis 3号库",
                    "synced_count": sync_count,
                    "redis_db": 3,
                    "example_key": f"seckill:stock:{seckill_goods.first().id}"  # 实际商品ID示例
                })
            else:
                # 同步0个商品 → 返回8002（非失败，只是没符合条件的商品）
                return SeckillResponse.other({
                    "message": "秒杀库存初始化完成，但未同步到任何商品",
                    "synced_count": 0,
                    "reason": "可能原因：1. 没有标记为秒杀的商品（is_seckill=True）；2. 所有秒杀商品已结束（seckill_end_time≤当前时间）",
                    "redis_db": 3
                })

        except Exception as e:
            # 捕获其他未预料的异常 → 返回8001（失败）
            return SeckillResponse.failed({
                "message": "秒杀库存初始化过程中出现未知错误",
                "error": str(e)[:50]
            })
# ================== 用户行为埋点 ==================
class GoodsBehaviorAPIView(APIView):
    def post(self, request, sku_id):
        try:
            # 第一步：判断是否未登录
            if isinstance(request.user, AnonymousUser):
                return ResponseMessage.GoodsResponse.failed("请先登录后再操作")
            
            # 第二步：登录用户 → 校验字典+status
            if not isinstance(request.user, dict) or not request.user.get('status'):
                return ResponseMessage.GoodsResponse.failed("用户登录状态异常，请重新登录")
            
            # 第三步：取user_id并埋点
            user_id = request.user.get('data', {}).get('user_id')
            if not user_id:
                return ResponseMessage.GoodsResponse.failed("用户ID不存在，请重新登录")
            
            record_user_behavior(user_id, sku_id)
            return ResponseMessage.GoodsResponse.success("行为记录成功")
        except Exception as e:
            logging.error(f"行为埋点失败：{str(e)}", exc_info=True)
            return ResponseMessage.GoodsResponse.failed("行为记录失败")

class RecommendView(APIView):
    def get(self, request):
        try:
            # 第一步：判断未登录 → 直接返回提示
            if isinstance(request.user, AnonymousUser):
                return ResponseMessage.GoodsResponse.failed("请先登录后查看推荐商品")
            
            # 第二步：登录用户 → 校验字典+提取user_id
            if not isinstance(request.user, dict):
                return ResponseMessage.GoodsResponse.failed("用户登录状态异常，请重新登录")
            
            user_data = request.user.get('data', {})
            user_id = user_data.get('user_id')
            if not user_id:
                return ResponseMessage.GoodsResponse.failed("请先登录后查看推荐商品")

            # 1. 从Redis获取用户最近浏览行为
            recent = []
            try:
                r = get_redis_connection('default')
                recent = list(r.smembers(f"user:behavior:{user_id}"))
            except Exception as e:
                logging.warning(f"Redis获取浏览行为失败：{str(e)}")

            if not recent:
                # 2. 无历史行为：优先查数据库热门商品（不依赖ES）
                try:
                    hot_goods = Goods.objects.all().order_by('-comment_count')[:10]
                    hot_data = GoodsSerializer(hot_goods, many=True).data
                    # 🔥 只传data，删掉提示语参数
                    return ResponseMessage.GoodsResponse.success(hot_data)
                except Exception as e:
                    logging.error(f"数据库查热门商品失败：{str(e)}")
                    # 🔥 只传空列表，删掉提示语
                    return ResponseMessage.GoodsResponse.success([])

            # 3. 有历史行为：尝试ES查相似，失败则查数据库
            seed = recent[0].decode('utf-8')
            data = []
            try:
                es = Elasticsearch(['localhost:9200'], timeout=5)
                s = Search(using=es, index='goods').query(
                    'more_like_this',
                    fields=['name'],
                    like=[{'_index': 'goods', '_id': seed}]
                ).exclude('term', id=seed)[:10]
                response = s.execute()

                for hit in response:
                    goods_id = getattr(hit, 'id', None)
                    if not goods_id:
                        continue
                    goods = Goods.objects.filter(id=goods_id).first()
                    if goods:
                        data.append({
                            "id": goods.id,
                            "name": goods.name,
                            "price": float(goods.jd_price) if goods.jd_price else 0.0,
                            "image": goods.image or ""
                        })
            except Exception as e:
                logging.warning(f"ES相似商品查询失败：{str(e)}")
                # ES失败，直接查数据库相似（按分类）
                try:
                    seed_goods = Goods.objects.filter(id=seed).first()
                    if seed_goods:
                        similar_goods = Goods.objects.filter(
                            type_id=seed_goods.type_id
                        ).exclude(id=seed).order_by('-comment_count')[:10]
                        data = GoodsSerializer(similar_goods, many=True).data
                except Exception as e2:
                    logging.error(f"数据库查相似商品失败：{str(e2)}")

            # 4. 补充热门商品（如果数据不足）
            if len(data) < 10:
                try:
                    need_count = 10 - len(data)
                    hot_goods = Goods.objects.exclude(id=seed).order_by('-comment_count')[:need_count]
                    hot_data = GoodsSerializer(hot_goods, many=True).data
                    data.extend(hot_data)
                except Exception as e:
                    pass

            # 5. 去重 + 兜底
            unique_data = list({item['id']: item for item in data}.values())[:10]
            # 🔥 只传data，删掉提示语
            return ResponseMessage.GoodsResponse.success(unique_data)
        except Exception as e:
            logging.error(f"推荐商品接口失败：{str(e)}", exc_info=True)
            # 🔥 只传空列表，删掉提示语
            return ResponseMessage.GoodsResponse.success([])
        
# 2. 解决指标重复注册：先创建独立注册器，再定义指标
metrics_registry = CollectorRegistry()  # 独立注册器，避免全局冲突
redis_hit_rate_gauge = Gauge(
    'redis_key_hit_rate_percent',  # 指标名：Redis命中率（百分比）
    'Redis key hit rate (calculated from keyspace_hits / (keyspace_hits + keyspace_misses))',
    registry=metrics_registry  # 绑定到独立注册器
)

def custom_metrics(request):
    """
    暴露2类指标：
    1. 商品总数（django_model_goods_creations_total）
    2. Redis命中率（redis_key_hit_rate_percent）
    """
    # 3. 计算Redis命中率（使用秒杀专用Redis库，和业务保持一致）
    hit_rate_rounded = 0.0  # 初始化默认值
    try:
        redis_conn = get_redis_connection('seckill')  # 秒杀专用Redis库
        stats = redis_conn.info('stats')
        key_hits = stats.get('keyspace_hits', 0)
        key_misses = stats.get('keyspace_misses', 0)
        total_queries = key_hits + key_misses
        
        # 计算命中率（保留2位小数，避免除以0）
        hit_rate = (key_hits / total_queries) * 100 if total_queries > 0 else 0.0
        hit_rate_rounded = round(hit_rate, 2)
        redis_hit_rate_gauge.set(hit_rate_rounded)  # 更新指标
        
    except Exception as e:
        # 出错时记录日志，不影响整体接口
        logger = logging.getLogger(__name__)
        logger.error(f"计算Redis命中率失败：{str(e)}", exc_info=True)

    # 4. 商品总数指标
    goods_count = Goods.objects.count()
    
    # 5. 用注册器自动生成指标文本（避免手动拼接错误，同时解决重复）
    # 先手动添加商品总数指标到注册器（确保和命中率指标在同一注册器）
    goods_total_gauge = Gauge(
        'django_model_goods_creations_total',
        'Total number of Goods model insert operations',
        registry=metrics_registry
    )
    goods_total_gauge.set(goods_count)
    
    # 生成Prometheus格式文本
    metrics_text = generate_latest(metrics_registry)
    
    # 6. 返回指标数据
    return HttpResponse(metrics_text, content_type="text/plain; charset=utf-8")
    
@csrf_exempt
def simplejson_metrics(request):
    from datetime import datetime
    goods_count = Goods.objects.count()
    # 如果是 annotation 查询，返回空列表
    if request.path.endswith('/annotations'):
        return JsonResponse([], safe=False)
    # 正常指标查询：注意 JsonResponse 的参数是 [[...]]，括号要闭合
    return JsonResponse([
        {
            "target": "goods_creations_total",
            "datapoints": [[goods_count, int(datetime.now().timestamp() * 1000)]]
        }  # 这里的 } 不能少，对应前面的 {
    ], safe=False) 
    
    
#（一）缓存穿透：故意查不存在的商品，DB 被反复攻击    
# 1. 通俗理解缓存穿透
# 场景：有人恶意刷你的接口，反复查/api/goods/999999（999999 是不存在的商品 ID）；
# 问题：缓存里没有这个 key，所有请求都直接打数据库，数据库扛不住就崩了；
# 核心解法：就算是不存在的 key，也缓存一个空值（比如 ""），设置短期过期（5 分钟），让后续请求走缓存，不查 DB。

from django.core.cache import caches  # 修正：复数 caches（保留注释）
from django.views.decorators.cache import never_cache
from django.http import JsonResponse  # 新增：确保 JsonResponse 能正常使用（之前可能漏导入）
# 移除顶部的 from .models import Goods（移到函数内部，延迟加载）
import random
import time

# 缓存穿透测试视图：查询商品（存在/不存在都测）
@never_cache  # 禁用Django自带缓存，手动控制逻辑
def test_cache_penetration(request, goods_id):
    # 新增：延迟导入 Goods（移到函数内部，避免项目启动时触发指标注册）
    from .models import Goods  # 保留你的模型导入，只是移位置
    # 1. 定义缓存key（加test前缀，用test_redis库）
    cache_key = f"test:goods:{goods_id}"
    test_cache = caches["test_redis"]  # 用5号测试库

    # 2. 先查缓存
    goods_data = test_cache.get(cache_key)
    if goods_data is not None:  # 注意：空字符串""也会命中，避免穿透
        return JsonResponse({
            "code": 200 if goods_data != "" else 404,
            "msg": "命中缓存（防穿透）" if goods_data != "" else "商品不存在（已缓存空值）",
            "data": goods_data,
            "cache_key": cache_key
        })

    # 3. 缓存未命中，查数据库
    try:
        goods = Goods.objects.get(id=goods_id)
        # 组装商品数据
        goods_data = {
            "id": goods.id,
            "name": goods.name,
            "price": float(goods.p_price),  # 修正：你的模型里是 p_price，不是 price（避免报错）
            "stock": goods.seckill_stock  # 修正：你的模型里是 seckill_stock，不是 stock（避免报错）
        }
        # 🔥 核心修改：通过URL参数控制过期时间，无需切换注释
        # 带 ?random_expire=1 时用随机过期（测试雪崩），否则用固定3600秒（测试穿透、击穿）
        random_expire = request.GET.get("random_expire", "0") == "1"
        expire_time = 3600 + random.randint(0, 300) if random_expire else 3600
        
        # 写入缓存（统一用上面的 expire_time，无需注释切换）
        test_cache.set(cache_key, goods_data, expire_time)
        
        # （二）缓存雪崩：大批量商品缓存同时过期，DB 被瞬间打爆
        # 1. 通俗理解缓存雪崩
        # 场景：你双十一前给 1000 个商品缓存都设置了 2 小时过期，到点后 1000 个商品的缓存同时失效；
        # 问题：此时大量用户访问这些商品，所有请求都打数据库，数据库瞬间扛不住崩了；
        # 核心解法：给每个商品的缓存过期时间加「随机值」，让过期时间错开（比如 1 小时 ±5 分钟），避免 “集体失效”。
        # 🔥 现在无需注释切换：访问时带 ?random_expire=1 用随机过期，不带用固定过期
        return JsonResponse({
            "code": 200,
            "msg": f"命中数据库，已写入缓存（{'随机过期' if random_expire else '固定过期'}）",
            "data": goods_data,
            "expire_time": expire_time,  # 新增：返回过期时间，方便验证
            "cache_key": cache_key
        })
    except Goods.DoesNotExist:
        # 关键：不存在的商品，缓存空值5分钟（300秒）
        test_cache.set(cache_key, "", 300)
        return JsonResponse({
            "code": 404,
            "msg": "商品不存在，空值已缓存（防穿透）",
            "cache_key": cache_key
        })
        
# （三）缓存击穿：热门商品缓存过期，高并发下 DB 被单点击穿
# 1. 通俗理解缓存击穿
# 场景：你的爆款商品（比如 ID=1）缓存过期了，此时有 1000 个用户同时访问这个商品；
# 问题：缓存没命中，1000 个请求同时打数据库，把数据库 “单点打穿”；
# 核心解法：互斥锁 + 双重检查 —— 缓存过期后，只有一个请求能抢到锁去查 DB，其他请求等待后重新查缓存（此时 DB 已经把数据写回缓存），避免同时查 DB。
# 缓存击穿测试视图：热门商品高并发场景
@never_cache
def test_cache_breakdown(request):
    from .models import Goods  # 保留内部导入
    hot_goods_id = 1  # 假设ID=1是热门商品
    cache_key = f"test:goods:{hot_goods_id}"
    lock_key = f"test:lock:goods:{hot_goods_id}"  # 锁key，和缓存key对应
    test_cache = caches["test_redis"]  # 修正：复数 caches（原 cache["test_redis"]）

    # 第一次查缓存：命中直接返回
    goods_data = test_cache.get(cache_key)
    if goods_data:
        return JsonResponse({
            "code": 200,
            "msg": "命中缓存（热门商品）",
            "data": goods_data,
            "thread": "当前请求"
        })

    # 缓存未命中，尝试获取分布式锁（nx=True：不存在才设置，ex=5：5秒过期，防止死锁）
    lock_acquired = test_cache.set(lock_key, "locked", nx=True, timeout=5)
    if lock_acquired:
        try:
            # 双重检查：防止其他线程已经更新了缓存（比如等待的时间里，锁被释放，数据已写入）
            goods_data = test_cache.get(cache_key)
            if goods_data:
                return JsonResponse({
                    "code": 200,
                    "msg": "双重检查命中缓存",
                    "data": goods_data,
                    "thread": "当前请求（抢锁后双重检查）"
                })

            # 抢锁成功，查数据库
            goods = Goods.objects.get(id=hot_goods_id)
            goods_data = {
                "id": goods.id,
                "name": goods.name,
                "price": float(goods.p_price),  # 修正：p_price 对应模型字段
                "stock": goods.seckill_stock  # 修正：seckill_stock 对应模型字段
            }
            # 写入缓存（加随机过期时间，防雪崩）
            test_cache.set(cache_key, goods_data, 3600 + random.randint(0, 300))
            return JsonResponse({
                "code": 200,
                "msg": "抢锁成功，查DB后写入缓存",
                "data": goods_data,
                "thread": "当前请求（唯一查DB的线程）"
            })
        finally:
            # 关键：无论是否报错，都要释放锁（避免死锁）
            test_cache.delete(lock_key)
    else:
        # 未抢到锁，等待100ms后重试（模拟高并发下的等待）
        time.sleep(0.1)
        # 递归重试：重新查缓存
        return test_cache_breakdown(request)