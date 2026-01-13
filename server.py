import asyncio
import json
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


# ==========================
# MAIN HANDLER
# ==========================
async def handler(websocket):
    username = None
    try:
        # First message MUST contain username
        raw = await websocket.recv()
        data = json.loads(raw)

        if "username" not in data:
            await websocket.close()
            return

        username = data["username"]

        # If same user reconnects → replace old connection
        if username in CLIENTS:
            try:
                await CLIENTS[username].close()
            except:
                pass

        CLIENTS[username] = websocket
        print(f"[+] {username} connected")

        # Notify everyone instantly
        await broadcast_online_users()

        # ==========================
        # MESSAGE LOOP
        # ==========================
        async for raw in websocket:
            try:
                data = json.loads(raw)
                msg_type = data.get("type")

                # --------------------------
                # MESSAGE
                # --------------------------
                if msg_type == "message":
                    target = data.get("to")
                    text = data.get("text")

                    if not target or not text:
                        continue

                    if target in CLIENTS:
                        await CLIENTS[target].send(json.dumps({
                            "type": "message",
                            "from": username,
                            "text": text
                        }))

                # --------------------------
                # TYPING
                # --------------------------
                elif msg_type == "typing":
                    target = data.get("to")
                    status = data.get("status", False)

                    if target in CLIENTS:
                        await CLIENTS[target].send(json.dumps({
                            "type": "typing",
                            "from": username,
                            "status": status
                        }))

            except Exception as e:
                print("Message error:", e)

    except websockets.exceptions.ConnectionClosed:
        pass

    finally:
        if username and username in CLIENTS:
            del CLIENTS[username]
            print(f"[-] {username} disconnected")
            await broadcast_online_users()


# ==========================
# SERVER START
# ==========================
async def main():
    print("🚀 Chatify Backend running on ws://0.0.0.0:8765")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
