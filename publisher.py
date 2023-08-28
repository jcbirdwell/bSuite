import os
import subprocess
import shutil
from os import environ as env
from typing import Literal

BumpLevel = Literal['major', 'minor', 'patch']


def blocking_cmd(cmd: list, ctx='') -> list:
    outputs = []
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    for line in iter(p.stdout.readline, b''):
        if line:
            outputs.append(line.rstrip().decode())
    p.wait()

    if p.returncode != 0:
        raise Exception(f'failed {ctx if ctx else cmd} with code {p.returncode} after outputting {outputs}')

    return outputs


def bumpver(level: BumpLevel):
    print('bumping')
    bump = ['bumpver', 'update', f'--{level}']
    out = blocking_cmd(bump, 'bumpver failed')
    print(out)


def builder():
    print('building')

    if os.path.exists('last_dist'):
        shutil.rmtree('last_dist')
    if os.path.exists('dist'):
        shutil.move('dist', 'last_dist')

    os.mkdir('dist')

    build = ['python', '-m', 'build']
    outputs = blocking_cmd(build)
    print(outputs)


def twine_check():
    print('twine checking')
    check = ['twine', 'check', 'dist/*']
    outputs = blocking_cmd(check)
    file_checks = [('PASSED' in x) for x in outputs]

    if not all(file_checks):
        raise Exception('file checks failed', outputs, file_checks)

    print(outputs)


def twine_upload():
    if 'pypi_user' not in env or 'pypi_password' not in env:
        raise Exception('missing credentials')

    upload = ['twine', 'upload', 'dist/*', '-u', env.get('pypi_user'), '-p', env.get('pypi_password')]
    outputs = blocking_cmd(upload, 'twine upload')
    print(outputs)


if __name__ == '__main__':
    os.chdir('python/bSuite')
    bumpver('patch')
    builder()
    twine_check()
    twine_upload()
