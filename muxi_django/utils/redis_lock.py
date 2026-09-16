import redis
import time
from threading import Thread

def acquire_redis_lock(redis_conn, lock_key, task_id, expire=10):
    """
    原子性获取Redis锁（防死锁基础：SET NX EX 原子操作 + 自动过期）
    :param redis_conn: Redis连接对象
    :param lock_key: 锁key（按商品隔离：seckill:lock:goods:{product_id}）
    :param task_id: 任务唯一标识（防误删锁）
    :param expire: 锁过期时间（秒，避免任务异常导致死锁）
    :return: True=获取成功，False=获取失败
    """
    # 核心：SET NX EX 原子操作（一步完成“不存在则设置”+“过期时间”，无中间态）
    # nx=True：只有key不存在时才设置
    # ex=expire：自动过期，防死锁
    result = redis_conn.set(lock_key, task_id, nx=True, ex=expire)
    return result is True

def release_redis_lock(redis_conn, lock_key, task_id):
    """
    原子性释放Redis锁（防死锁：验证锁归属，避免误删）
    :param redis_conn: Redis连接对象
    :param lock_key: 锁key
    :param task_id: 任务唯一标识（与加锁时一致）
    :return: True=释放成功，False=释放失败（锁已过期/非当前任务持有）
    """
    # Lua脚本：原子执行“判断归属+删除”，避免多线程并发下的误删问题
    unlock_script = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    else
        return 0
    end
    """
    # 执行脚本：1个key（lock_key），1个参数（task_id）
    release_result = redis_conn.eval(unlock_script, 1, lock_key, task_id)
    return release_result == 1

def lock_renewal(redis_conn, lock_key, task_id, expire=10, interval=3):
    """
    锁续约（进阶防死锁：任务耗时超过锁过期时间时，自动延长锁有效期）
    :param redis_conn: Redis连接对象
    :param lock_key: 锁key
    :param task_id: 任务唯一标识
    :param expire: 锁原始过期时间
    :param interval: 续约间隔（秒，小于过期时间）
    """
    def renew():
        while True:
            # 先判断锁是否还属于当前任务
            if redis_conn.get(lock_key) != task_id.encode('utf-8'):
                # 锁已过期/被释放，停止续约
                break
            # 原子续约：重置过期时间（仅当锁存在且归属当前任务时）
            renew_script = """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('expire', KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            renew_result = redis_conn.eval(renew_script, 1, lock_key, task_id, expire)
            if renew_result != 1:
                break
            # 每隔interval秒续约一次
            time.sleep(interval)

    # 启动后台线程续约，不阻塞主任务
    renewal_thread = Thread(target=renew, daemon=True)
    renewal_thread.start()
    return renewal_thread