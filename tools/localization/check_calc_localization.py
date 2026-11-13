"""One command: check calculator display in a fresh copy, without user saves."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='pob-calc-locale-') as directory:
        workspace = Path(directory)
        shutil.copytree(ROOT / 'src', workspace / 'src',
                        ignore=shutil.ignore_patterns('Builds', 'Settings.xml', 'language.cfg', '__pycache__'))
        shutil.copy2(ROOT / 'manifest.xml', workspace / 'manifest.xml')
        checks = [
            ('test_locale.py',),
            ('test_calc_identifiers.py',),
            ('test_calc_panel_locale.py',),
            ('test_calc_buff_lists.py',),
            ('test_interface_ui.py',),
            ('test_item_search.py',),
            ('test_imported_item_tooltips.py', '--workspace', str(workspace)),
            ('audit_calc_breakdown.py', '--workspace', str(workspace)),
            ('test_layout.py', '--workspace', str(workspace)),
        ]
        for check, *arguments in checks:
            subprocess.run([sys.executable, str(HERE / check), *arguments], cwd=ROOT, check=True)
    print('Calculator localization checks passed in a fresh isolated workspace')
