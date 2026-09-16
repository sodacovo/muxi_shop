from django_redis import get_redis_connection

def record_user_behavior(user_id, sku_id):
    r = get_redis_connection('default')
    key = f"user:behavior:{user_id}"
    r.sadd(key, sku_id)
    if r.scard(key) > 5:
        r.spop(key) 