import pika
import json
from django.db import transaction
from django.conf import settings
from goods.models import Goods
from stock.models import StockTx
from order.models import EventLog
from order.tasks import send_event_to_rabbitmq

def consume_order_events():
    try:
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER or 'guest',
            settings.RABBITMQ_PASS or 'guest'
        )
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST or 'localhost',
                port=5672,
                virtual_host='/'
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue='order_events', durable=True)

        def callback(ch, method, properties, body):
            try:
                msg = json.loads(body.decode('utf-8'))
                event_id = msg['event_id']
                event_type = msg['event_type']
                event_data = msg['data']

                if EventLog.objects.filter(event_id=event_id, status='consumed').exists():
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    print(f"事件{event_id}已消费，跳过")
                    return

                if event_type == 'OrderCreated':
                    order_trade_no = event_data['order_trade_no']
                    goods_id = event_data['goods_id']
                    qty = event_data['qty']

                    with transaction.atomic():
                        goods = Goods.objects.select_for_update().get(id=goods_id, is_seckill=True)
                        if goods.seckill_stock < qty:
                            compensate_event = EventLog.objects.create(
                                event_type='CompensateOrder',
                                data={'order_trade_no': order_trade_no, 'reason': 'stock_insufficient', 'goods_id': goods_id},
                                status='pending'
                            )
                            send_event_to_rabbitmq.delay(compensate_event.event_id)
                            EventLog.objects.filter(event_id=event_id).update(status='consumed')
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                            print(f"订单{order_trade_no}库存不足，已发补偿事件")
                            return

                        goods.seckill_stock -= qty
                        goods.save()

                        StockTx.objects.create(
                            order_trade_no=order_trade_no,
                            goods_id=goods_id,
                            qty=qty,
                            tx_status='deducted'
                        )

                        deduct_event = EventLog.objects.create(
                            event_type='StockDeducted',
                            data={'order_trade_no': order_trade_no, 'goods_id': goods_id, 'remaining_stock': goods.seckill_stock},
                            status='pending'
                        )
                        send_event_to_rabbitmq.delay(deduct_event.event_id)

                    EventLog.objects.filter(event_id=event_id).update(status='consumed')
                    print(f"订单{order_trade_no}库存扣减成功，剩余库存：{goods.seckill_stock}")

                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                print(f"消费事件失败：{str(e)}，不ACK，等待重试")

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue='order_events', on_message_callback=callback)
        print("库存服务开始监听order_events队列...")
        channel.start_consuming()

    except Exception as e:
        print(f"消费脚本启动失败：{str(e)}")

if __name__ == '__main__':
    consume_order_events()