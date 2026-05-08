from App import create_app
import redis
import os
app = create_app()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
