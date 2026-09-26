import argparse
import logging
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".opennotebook")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--web-dir", type=Path)
    parser.add_argument("--mcp", action="store_true")
    parser.add_argument("--notebook")
    parser.add_argument("--parse-document", type=Path)
    parser.add_argument("--parse-output", type=Path)
    parser.add_argument("--parse-url")
    parser.add_argument("--parent-pid", type=int)
    parser.add_argument("--parser-memory", type=int, default=512)
    parser.add_argument("--parser-seconds", type=float, default=60)
    args = parser.parse_args()
    if args.parse_document or args.parse_url:
        if not args.parse_output or not args.parent_pid:
            parser.error("The parser requires an output file and parent process.")
        from on_knowledge.features.sources.parser_worker import run_worker

        run_worker(
            args.parse_document,
            args.parse_output,
            args.parent_pid,
            args.parser_memory,
            args.parser_seconds,
            args.parse_url,
        )
        return
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    if args.mcp:
        if not args.notebook:
            parser.error("--mcp requires --notebook to restrict access")
        from on_knowledge.mcp_server import run_mcp

        run_mcp(args.data_dir, args.notebook)
    else:
        import uvicorn
        from on_knowledge.app import create_app

        token = os.getenv("OPENNOTEBOOK_SESSION_TOKEN")
        if not token or len(token) < 24:
            parser.error("OPENNOTEBOOK_SESSION_TOKEN must contain at least 24 characters")
        app = create_app(args.data_dir, token, args.web_dir)
        uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
