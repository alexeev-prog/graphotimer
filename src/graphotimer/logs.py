from rich.console import Console


def log_error(text: str, console: Console):
    console.print(f"[red bold][ ERROR ][/red bold] {text}")
    exit()


def log_info(text: str, console: Console):
    console.print(f"[green bold][ INFO  ][/green bold] {text}")


def log_warn(text: str, console: Console):
    console.print(f"[yellow bold][ WARN  ][/yellow bold] {text}")


def log_debug(text: str, console: Console):
    console.print(f"[BLUE bold][ DEBUG ][/BLUE bold] {text}")
