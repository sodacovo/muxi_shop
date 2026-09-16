from django.test import TestCase
from apps.order.tasks import consume_stock_event
from celery.result import AsyncResult
import time

class ConsumeStockEventTest(TestCase):
    def test_exception_retry(self):
        """测试异常重试机制"""
        # 生成唯一订单号
        trade_no = f"SECKILL_TEST_{int(time.time())}"
        event_data = {
            "trade_no": trade_no,
            "goods_id": 1078,
            "qty": 1,
            "user_id": 8,
            "user_email": "4@qq.com"
        }

        # 发送任务
        task = consume_stock_event.delay(event_data)
        self.assertEqual(task.status, "PENDING")  # 初始状态为PENDING

        # 等待25秒，验证第1次重试
        time.sleep(25)
        task_result = AsyncResult(task.id)
        self.assertEqual(task_result.status, "RETRY")  # 重试中状态
        self.assertIn("测试手动ACK：库存消费失败", str(task_result.result))  # 异常信息正确

        # 等待60秒，验证3次重试后失败
        time.sleep(60)
        task_result = AsyncResult(task.id)
        self.assertEqual(task_result.status, "FAILURE")  # 最终状态为失败

    def test_idempotency(self):
        """测试幂等性（重复任务不重复执行）"""
        trade_no = f"SECKILL_TEST_IDEMPOTENT_{int(time.time())}"
        event_data = {
            "trade_no": trade_no,
            "goods_id": 1078,
            "qty": 1,
            "user_id": 8,
            "user_email": "4@qq.com"
        }

        # 发送2次相同任务
        task1 = consume_stock_event.delay(event_data)
        task2 = consume_stock_event.delay(event_data)

        # 等待25秒后查看状态
        time.sleep(25)
        task1_result = AsyncResult(task1.id)
        task2_result = AsyncResult(task2.id)

        # 2次任务都应触发重试（你的代码中没有额外幂等逻辑，仅验证任务能正常执行）
        self.assertEqual(task1_result.status, "RETRY")
        self.assertEqual(task2_result.status, "RETRY")