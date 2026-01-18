import asyncio
import json
import os
import websockets

# ==========================
# GLOBAL STATE
# ==========================
CLIENTS = {}  # username -> websocket


# ==========================
# HELPERS
# ==========================
async def broadcast_online_users():
    """Send online users list to everyone"""
    if not CLIENTS:
        return

    message = json.dumps({
        "type": "online_users",
        "users": list(CLIENTS.keys())
    })

    await asyncio.gather(
        *[ws.send(message) for ws in CLIENTS.values()],
        return_exceptions=True
    )


async def safe_send(ws, message):
    try:
        await ws.send(message)
    except:
        pass


# ==========================
# MAIN HANDLER
# ==========================
async def handler(websocket):
    username = None

    try:
        # ---- First message must contain username ----
        raw = await websocket.recv()
        data = json.loads(raw)

        if "username" not in data:
            await websocket.close()
            return

        username = data["username"]

        # ---- Replace old connection if exists ----
        if username in CLIENTS:
            try:
                await CLIENTS[username].close()
            except:
                pass

        CLIENTS[username] = websocket
        print(f"[+] {username} connected")

        await broadcast_online_users()

        # ---- Message loop ----
        async for raw in websocket:
            try:
                data = json.loads(raw)
                msg_type = data.get("type")

                # ---------- HEARTBEAT ----------
                if msg_type == "ping":
                    continue

                # ---------- MESSAGE ----------
                if msg_type == "message":
                    target = data.get("to")
                    text = data.get("text")

                    if target and text and target in CLIENTS:
                        await safe_send(
                            CLIENTS[target],
                            json.dumps({
                                "type": "message",
                                "from": username,
                                "text": text
                            })
                        )

                # ---------- TYPING ----------
                elif msg_type == "typing":
                    target = data.get("to")
                    status = data.get("status", False)

                    if target in CLIENTS:
                        await safe_send(
                            CLIENTS[target],
                            json.dumps({
                                "type": "typing",
                                "from": username,
                                "status": status
                            })
                        )

            except Exception as e:
                print("Message error:", e)

    except websockets.exceptions.ConnectionClosed:
        pass

    finally:
        # ---- Cleanup on disconnect ----
        if username and username in CLIENTS:
            del CLIENTS[username]
            print(f"[-] {username} disconnected")
            await broadcast_online_users()


# ==========================
# SERVER START (RENDER SAFE)
# ==========================
async def main():
    PORT = int(os.environ.get("PORT", 10000))
    print(f"🚀 Chatify Backend running on port {PORT}")

    async with websockets.serve(
        handler,
        "0.0.0.0",
        PORT,
        ping_interval=None  # frontend handles heartbeat
    ):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
