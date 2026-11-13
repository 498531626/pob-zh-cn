"""Authorize Gitee in a user-run terminal without putting a token in chat or files."""
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]


def account_for_token(token):
    # Prefer the OAuth bearer header. Some Gitee endpoints require their documented
    # access_token query parameter; that URL stays in memory and is never logged.
    for use_query in (False, True):
        url = 'https://gitee.com/api/v5/user'
        headers = {'User-Agent': 'PoB-Gitee-Authorization'}
        if use_query:
            url += '?' + urlencode({'access_token': token})
        else:
            headers['Authorization'] = 'Bearer ' + token
        try:
            with urlopen(Request(url, headers=headers), timeout=20) as response:
                account = json.load(response)
            login = account.get('login', '')
            if not login or any(character in login for character in '\r\n='):
                raise ValueError('Gitee did not return a valid account login.')
            return login
        except HTTPError as error:
            if not use_query and error.code in (400, 401, 403):
                continue
            raise ValueError(f'Gitee authorization failed (HTTP {error.code}). Check token permissions.') from None
        except (URLError, TimeoutError):
            raise ValueError('Could not connect to Gitee. No credential was saved.') from None
    raise ValueError('Gitee authorization failed.')


def main():
    if not sys.stdin.isatty():
        raise ValueError('Run this script yourself in an interactive terminal so the token stays hidden.')
    helper = subprocess.run(['git', '-C', str(ROOT), 'config', '--get-all', 'credential.helper'],
                            capture_output=True, text=True, check=False)
    if helper.stdout.strip().splitlines() != ['manager']:
        raise ValueError('Expected Windows Git Credential Manager; refusing other credential storage.')
    print('Create a Gitee personal token with account-read and repository-management permissions:')
    print('https://gitee.com/profile/personal_access_tokens')
    token = getpass.getpass('Gitee token (hidden input): ').strip()
    if not token or any(character in token for character in '\r\n'):
        raise ValueError('Empty or invalid token.')
    login = account_for_token(token)
    environment = os.environ.copy()
    environment.update({'GCM_INTERACTIVE': 'never', 'GIT_TERMINAL_PROMPT': '0'})
    result = subprocess.run(['git', '-C', str(ROOT), 'credential', 'approve'],
                            input=f'protocol=https\nhost=gitee.com\nusername={login}\npassword={token}\n\n',
                            capture_output=True, text=True, env=environment, timeout=20)
    if result.returncode:
        raise ValueError('Credential Manager could not save the authorization.')
    print('Gitee authorized for account: ' + login)
    print('Saved in Windows Credential Manager. No repository has been created or pushed yet.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, subprocess.TimeoutExpired, KeyboardInterrupt) as error:
        print('Authorization cancelled.' if isinstance(error, KeyboardInterrupt) else str(error), file=sys.stderr)
        raise SystemExit(1)
