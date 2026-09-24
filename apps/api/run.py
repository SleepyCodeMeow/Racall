import argparse
import logging
import os
import sys
from pathlib import Path

import uvicorn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".opennotebook")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--web-dir", type=Path)
    parser.add_argument("--mcp", action="store_true")
    parser.add_argument("--notebook")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    if args.mcp:
        if not args.notebook:
            parser.error("--mcp requires --notebook to restrict access")
        from on_knowledge.mcp_server import run_mcp
        run_mcp(args.data_dir, args.notebook)
    else:
        from on_knowledge.app import create_app
        token = os.getenv("OPENNOTEBOOK_SESSION_TOKEN")
        if not token or len(token) < 24:
            parser.error("OPENNOTEBOOK_SESSION_TOKEN must contain at least 24 characters")
        app = create_app(args.data_dir, token, args.web_dir)
        uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
