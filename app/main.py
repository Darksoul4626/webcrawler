import argparse
import asyncio

from app.config import load_config
from app.scheduler import run_scheduler, run_topic_once


def parse_args():
    p = argparse.ArgumentParser(description="Automated web crawler")
    p.add_argument("--config", default="crawler.config.yaml", help="Path to config file")
    p.add_argument("--once", action="store_true", help="Run one topic once, then exit")
    p.add_argument("--topic", default=None, help='Topic name for --once mode (exact match)')
    return p.parse_args()


def main():
    args = parse_args()
    cfg = load_config(args.config)

    if args.once:
        if not args.topic:
            raise SystemExit("Error: --once requires --topic \"<Topic Name>\"")
        asyncio.run(run_topic_once(cfg, args.topic))
        return

    asyncio.run(run_scheduler(cfg))


if __name__ == "__main__":
    main()