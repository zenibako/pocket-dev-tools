"""Optional per-case route: setup expression and input override."""
import json
import re


def validate(setup, buttons):
    route = {}
    if setup:
        # Becomes a C string literal and a "return EXPR" Lua chunk of at most 255 bytes.
        if not re.fullmatch(r'[ !#-\[\]-~]{1,200}', setup):
            raise ValueError('Setup expression must be 1-200 printable ASCII characters without quotes or backslashes')
        route['setup'] = setup
    if buttons != 'seed7':
        route['input'] = buttons
    return route


def flags(folder):
    path = folder / 'route.json'
    route = json.loads(path.read_text()) if path.exists() else {}
    out = []
    if route.get('setup'):
        out += ['-DP8P_RUNTIME_DEBUG', '-DPICO_SETUP="' + route['setup'] + '"']
    if route.get('input') == 'none':
        out.append('-DPICO_INPUT_NONE')
    return out
