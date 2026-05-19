# init_rabbitmq.py
import asyncio
import aio_pika

async def init():
    connection = await aio_pika.connect("amqp://nikos:12345@rabbitmq/")
    channel = await connection.channel()
    
    # Delete queues if they exist (to reset parameters)
    try:
        await channel.queue_delete("observations")
        print("Deleted existing 'observations' queue")
    except Exception as e:
        print(f"'observations' queue didn't exist or couldn't delete: {e}")
    
    try:
        await channel.queue_delete("observations.dlq")
        print("Deleted existing 'observations.dlq' queue")
    except Exception as e:
        print(f"'observations.dlq' queue didn't exist or couldn't delete: {e}")
    
    # Main observations queue
    queue = await channel.declare_queue(
        "observations",
        durable=True,
        arguments={"x-max-length": 50000, "x-overflow": "reject-publish"},
    )
    await queue.bind("amq.topic", routing_key="#.SENSOR")
    print("Queue 'observations' and binding created successfully")
    
    # Dead Letter Queue (DLQ) for failed messages
    dlq = await channel.declare_queue(
        "observations.dlq",
        durable=True,
        arguments={"x-max-length": 10000, "x-overflow": "reject-publish"},
    )
    print("Dead Letter Queue 'observations.dlq' created successfully")
    
    await connection.close()

asyncio.run(init())