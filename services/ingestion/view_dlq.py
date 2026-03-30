#!/usr/bin/env python3
"""
View messages in the Dead Letter Queue (DLQ)

Usage:
    python view_dlq.py [--count N]
"""
import asyncio
import aio_pika
import json
import sys
import argparse
from datetime import datetime


async def view_dlq(count: int = 10):
    """View messages in the DLQ without removing them"""
    connection = await aio_pika.connect("amqp://nikos:12345@rabbitmq/")
    channel = await connection.channel()
    dlq = await channel.declare_queue("observations.dlq", durable=True)
    
    message_count = dlq.declaration_result.message_count
    print(f"\n{'='*80}")
    print(f"Dead Letter Queue: observations.dlq")
    print(f"Total messages: {message_count}")
    print(f"{'='*80}\n")
    
    if message_count == 0:
        print("✅ DLQ is empty - no failed messages")
        await connection.close()
        return
    
    # Get messages (up to count)
    messages_viewed = 0
    async with dlq.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                messages_viewed += 1
                
                # Parse message
                try:
                    body = json.loads(message.body.decode())
                except:
                    body = message.body.decode()
                
                # Extract metadata
                retry_count = message.headers.get("x-retry-count", "unknown") if message.headers else "unknown"
                failed_at = message.headers.get("x-failed-at", "unknown") if message.headers else "unknown"
                original_key = message.headers.get("x-original-routing-key", "unknown") if message.headers else "unknown"
                
                print(f"Message #{messages_viewed}")
                print(f"  Failed at: {failed_at}")
                print(f"  Retry count: {retry_count}")
                print(f"  Original routing key: {original_key}")
                print(f"  Body: {json.dumps(body, indent=2)}")
                print(f"  {'-'*76}\n")
                
                if messages_viewed >= count:
                    break
    
    if messages_viewed < message_count:
        print(f"Showing {messages_viewed} of {message_count} messages (use --count to see more)")
    
    await connection.close()


async def purge_dlq():
    """Delete all messages from DLQ"""
    connection = await aio_pika.connect("amqp://nikos:12345@rabbitmq/")
    channel = await connection.channel()
    dlq = await channel.declare_queue("observations.dlq", durable=True)
    
    purged = await dlq.purge()
    print(f"✅ Purged {purged} messages from DLQ")
    
    await connection.close()


def main():
    parser = argparse.ArgumentParser(description="View or manage Dead Letter Queue messages")
    parser.add_argument("--count", "-n", type=int, default=10, help="Number of messages to view (default: 10)")
    parser.add_argument("--purge", action="store_true", help="Purge all messages from DLQ (use with caution!)")
    
    args = parser.parse_args()
    
    if args.purge:
        confirm = input("⚠️  Are you sure you want to purge ALL messages from DLQ? [y/N] ")
        if confirm.lower() == 'y':
            asyncio.run(purge_dlq())
        else:
            print("Cancelled")
    else:
        asyncio.run(view_dlq(args.count))


if __name__ == "__main__":
    main()
