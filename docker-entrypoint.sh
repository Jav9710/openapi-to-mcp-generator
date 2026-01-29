#!/bin/bash
set -e

# Default values
PORT=${PORT:-5000}
OUTPUT_DIR=${OUTPUT_DIR:-/app/output}
WORKERS=${WORKERS:-2}
THREADS=${THREADS:-4}

echo "Starting OpenAPI to MCP Generator Web Service..."
echo "  Port: $PORT"
echo "  Output Directory: $OUTPUT_DIR"
echo "  Workers: $WORKERS"
echo "  Threads: $THREADS"

# Run with gunicorn for production
exec python -c "
import sys
sys.path.insert(0, '/app')

from src.openapi_to_mcp.gui.web_app import create_app

app = create_app(
    spec=None,
    spec_path=None,
    output_dir='${OUTPUT_DIR}',
    standalone=True
)

if __name__ == '__main__':
    from gunicorn.app.base import BaseApplication

    class StandaloneApplication(BaseApplication):
        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super().__init__()

        def load_config(self):
            for key, value in self.options.items():
                if key in self.cfg.settings and value is not None:
                    self.cfg.set(key.lower(), value)

        def load(self):
            return self.application

    options = {
        'bind': '0.0.0.0:${PORT}',
        'workers': ${WORKERS},
        'threads': ${THREADS},
        'timeout': 120,
        'accesslog': '-',
        'errorlog': '-',
        'capture_output': True,
    }

    StandaloneApplication(app, options).run()
"
