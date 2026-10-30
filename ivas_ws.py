import os
import ssl
import json
import time
import websocket


class IvasWebSocket:
    def __init__(self, ws_token, ws_user, url=None, on_message=None):
        self.ws_token = ws_token
        self.ws_user = ws_user
        self.url = url or os.getenv("IVAS_WS_URL", "wss://www.ivasms.com/ws")
        self.on_message = on_message
        self.ws = None

    def _headers(self):
        return [
            f"Authorization: Bearer {self.ws_token}",
            f"X-WS-User: {self.ws_user}",
        ]

    def connect(self):
        def on_msg(ws, message):
            if self.on_message:
                self.on_message(message)
            else:
                print("WS:", message)

        def on_err(ws, err):
            print("WS error:", err)

        def on_close(ws, code, msg):
            print("WS closed:", code, msg)

        self.ws = websocket.WebSocketApp(
            self.url,
            header=self._headers(),
            on_message=on_msg,
            on_error=on_err,
            on_close=on_close,
        )
        # run in foreground; caller can thread it
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def send_auth(self):
        if self.ws:
            payload = {"token": self.ws_token, "user": self.ws_user}
            self.ws.send(json.dumps(payload))
