"""
CLI entry point.

Usage:
    python -m src.main "Mo vnexpress.net, click bai viet dau tien, cuon xuong"
    python -m src.main "Open google.com and search for Python" --name search-demo
"""
"""
CLI entry point.

Usage:
    python -m src.main "Mo vnexpress.net, click bai viet dau tien, cuon xuong"
    python -m src.main "Open google.com and search for Python" --name search-demo
"""
import sys
from .pipeline import run_pipeline


def main():
    """CLI entry point: python -m src.main "<command>" [--name <video-name>]"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Tao video huong dan tu kich ban ngon ngu tu nhien."
    )
    parser.add_argument("command", nargs="+", help="Kich ban huong dan (tieng Viet hoac tieng Anh)")
    parser.add_argument("--name", default="demo", help="Ten video (default: demo)")

    args = parser.parse_args()
    user_input = " ".join(args.command)

    try:
        run_pipeline(user_input, video_name=args.name)
    except Exception as exc:
        print(f"LOI: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
