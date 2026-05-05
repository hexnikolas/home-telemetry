# init_rabbitmq.py
import asyncio
import aio_pika

async def init():
    connection = await aio_pika.connect("amqp://nikos:12345@rabbitmq/")
    channel = await connection.channel()
    
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