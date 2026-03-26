# init_rabbitmq.py
import asyncio
import aio_pika

async def init():
    connection = await aio_pika.connect("amqp://nikos:12345@rabbitmq/")
    channel = await connection.channel()
    queue = await channel.declare_queue("observations", durable=True)
    await queue.bind("amq.topic", routing_key="#.SENSOR")
    print("Queue and binding created successfully")
    await connection.close()

asyncio.run(init())