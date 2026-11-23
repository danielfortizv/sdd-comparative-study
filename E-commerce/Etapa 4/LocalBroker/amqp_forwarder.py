"""Local TCP bridge to real WSL RabbitMQ, with a dependency-free AMQP probe."""
import argparse
import asyncio
import socket
import subprocess
import sys


def probe(host):
    """Require AMQP 0-9-1 Connection.Start, not just an open port."""
    try:
        with socket.create_connection((host, 5672), timeout=1) as connection:
            connection.settimeout(1)
            connection.sendall(b"AMQP\x00\x00\x09\x01")
            response = b""
            while len(response) < 11:
                chunk = connection.recv(11 - len(response))
                if not chunk:
                    return False
                response += chunk
            return response[:3] == b"\x01\x00\x00" and response[7:11] == b"\x00\x0a\x00\x0a"
    except OSError:
        return False


async def copy(reader, writer):
    while data := await reader.read(65536):
        writer.write(data)
        await writer.drain()


async def serve(host):
    async def handle(reader, writer):
        upstream = None
        tasks = []
        try:
            other, upstream = await asyncio.wait_for(asyncio.open_connection(host, 5672), timeout=5)
            tasks = [asyncio.create_task(copy(reader, upstream)), asyncio.create_task(copy(other, writer))]
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        except (OSError, asyncio.TimeoutError) as error:
            print(f"RabbitMQ relay connection failed: {error}", file=sys.stderr, flush=True)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            writer.close()
            if upstream:
                upstream.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 5672)
    print(f"127.0.0.1:5672 -> real RabbitMQ {host}:5672", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", metavar="HOST")
    parser.add_argument("--upstream", metavar="HOST")
    args = parser.parse_args()
    if args.probe:
        raise SystemExit(0 if probe(args.probe) else 1)
    host = args.upstream or subprocess.check_output(
        ["wsl", "-d", "Ubuntu", "--", "hostname", "-I"], text=True, timeout=20
    ).strip().split()[0]
    asyncio.run(serve(host))
