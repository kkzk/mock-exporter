# JSONメッセージを送信
Invoke-RestMethod -Uri "http://localhost:8000/webhook/" -Method POST -ContentType "application/json" -Body '{"message": "Hello from webhook!"}'

# プレーンテキストを送信
Invoke-RestMethod -Uri "http://localhost:8000/webhook/" -Method POST -ContentType "text/plain" -Body "Simple text message"

# 起動用コマンド
`uv run daphne mock_exporter.asgi:application -p 3003`

