import typer

from DashAI.__main__ import main

if __name__ == "__main__":
    typer.run(lambda: main(webview=True))
