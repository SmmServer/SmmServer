# SmmServer

Open source private server for Super Mario Maker, integrated with [smmdb](https://smmdb.net) and [Cemu](https://cemu.info).

![screenshot](https://i.imgur.com/hmaCINN.png)

![cemu](https://i.imgur.com/DqrNdic.png)

## Compiling

Install [`uv`](https://docs.astral.sh/uv/), then:

```bash
# Create venv with dependencies
uv sync

# Create package
uv run PyInstaller SmmServer.spec
```

The release package also has a copy of [Cemu 2.6](https://github.com/cemu-project/Cemu/releases/tag/v2.6) and a few configuration files.
