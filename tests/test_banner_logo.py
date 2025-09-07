from colorama import Fore, init
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model.cli import animate_banner


def test_animate_banner_has_two_colours(capsys):
    init(autoreset=True, strip=False)
    animate_banner(frames=0)
    out = capsys.readouterr().out
    assert Fore.CYAN in out
    assert Fore.LIGHTRED_EX in out
