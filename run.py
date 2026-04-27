from __future__ import annotations

try:
    from overstats.config import get_api_config
    from overstats.src import create_server
except ModuleNotFoundError:
    from config import get_api_config
    from src import create_server


def main() -> None:
    config = get_api_config()
    server = create_server(config)
    print(
        f"[overstats] serving on http://{config.host}:{config.port} "
        f"(default_stream={config.use_stream_response})"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
