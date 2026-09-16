import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger('app')

class SeckillResultConsumer(AsyncWebsocketConsumer):
    """处理秒杀结果的实时推送"""
    async def connect(self):
        try:
            # 打印 scope 信息，确认 task_id 是否能提取到
            logger.info(f"[WebSocket连接] 开始处理，scope: {self.scope}")
            
            # 提取 task_id（从 URL 路由参数）
            self.task_id = self.scope['url_route']['kwargs'].get('task_id')
            if not self.task_id or len(self.task_id) < 10:
                logger.error(f"[WebSocket连接失败] task_id 无效：{self.task_id}")
                await self.close(code=4001)
                return
            
            self.group_name = f'seckill_{self.task_id}'
            # 加入分组
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            
            logger.info(f"[WebSocket连接成功] task_id={self.task_id}，group_name={self.group_name}，channel_name={self.channel_name}")
        except Exception as e:
            logger.error(f"[WebSocket连接异常] 错误：{str(e)}", exc_info=True)
            await self.close(code=1011)

    async def seckill_result(self, event):
        try:
            result = event['result']
            if not isinstance(result, dict) or 'code' not in result:
                raise ValueError(f"推送数据格式错误：{result}")
            
            # 打印要发送给前端的数据
            logger.info(f"[WebSocket推送] task_id={self.task_id}，发送数据：{result}")
            await self.send(text_data=json.dumps(result))
            logger.info(f"[WebSocket推送成功] task_id={self.task_id}")
        except Exception as e:
            logger.error(f"[WebSocket推送失败] task_id={self.task_id}，错误：{str(e)}", exc_info=True)

    async def disconnect(self, close_code):
        # 断开连接时退出分组
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"[WebSocket断开] task_id={self.task_id}，close_code={close_code}")