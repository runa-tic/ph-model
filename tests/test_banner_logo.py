from colorama import Fore, init
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model.cli import print_banner


def test_banner_colours_half_spheres_only(capsys):
    init(autoreset=True, strip=False)
    print_banner()
    out = capsys.readouterr().out
    assert Fore.CYAN + "=" in out
    assert Fore.LIGHTRED_EX + "=" in out
    assert Fore.CYAN + "-" in out
    assert Fore.WHITE + "-" not in out
    assert Fore.LIGHTRED_EX + "-" not in out
    assert Fore.CYAN + "." not in out
    assert Fore.LIGHTRED_EX + "." not in out
