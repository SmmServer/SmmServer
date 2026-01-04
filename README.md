# SmmServer

Open source private server for Super Mario Maker, integrated with [smmdb](https://smmdb.net) and [Cemu](https://cemu.info).

![screenshot](https://i.imgur.com/hmaCINN.png)

![cemu](https://i.imgur.com/DqrNdic.png)

## Compiling


First, create a venv with `python -m venv venv`, enter the venv with `venv/Scripts/Activate.ps1`,  install the required dependencies with `pip install -r requirements.txt`, then compile with `python -m PyInstaller SmmServer.spec`
