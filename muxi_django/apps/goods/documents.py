from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from .models import Goods

"""
  将Dajngo模型（如Goods）与ES索引字段关联，指定分词策略、字段类型
  相当于ES的“数据模型”。
"""

# 新增：替换旧IP为HTTPS域名的工具函数
def replace_old_ip_to_https(url):
    if not url:
        return ""
    # 关键：把旧IP的HTTP URL 替换成 新域名的HTTPS URL
    return url.replace(
        "http://8.138.126.24/static/product_images/",
        "https://www.nwq1309.shop/static/product_images/"
    )

@registry.register_document
class GoodsDocument(Document):
    # 1. 保留你原有的配置（id和name字段）
    id = fields.LongField()  
    name = fields.TextField(
        analyzer='ik_max_word',
        fields={'raw': fields.KeywordField()}
    )

    class Index:
        name = 'goods'  # 索引名不变，和你原有配置一致
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
            'analysis': {
                'analyzer': {
                    'ik_max_word': {'type': 'ik_max_word'}
                }
            }
        }

    class Django:
        model = Goods
        fields = ['jd_price', 'image']  # 保留你原有的字段配置

    # 新增：重写prepare_image方法，同步数据到ES时自动替换URL
    def prepare_image(self, instance):
        """
        instance：Django的Goods模型实例
        返回值：存入ES的image字段值（已替换为新域名）
        """
        # 情况1：如果Goods模型的image字段存的是「完整旧IP URL」（如 http://8.138.126.24/xxx.jpg）
        if instance.image and instance.image.startswith("http://8.138.126.24"):
            return replace_old_ip_to_https(instance.image)
        
        # 情况2：如果Goods模型的image字段存的是「相对路径」（如 100016905259.jpg）
        elif instance.image:
            return f"https://www.nwq1309.shop/static/product_images/{instance.image}"
        
        # 情况3：无图片时返回空字符串
        return ""