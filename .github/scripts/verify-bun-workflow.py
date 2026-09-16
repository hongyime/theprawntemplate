"""Exercise the repository-owned build workflow with synthetic local dependencies."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import ast
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/ci.yml'
FIXTURES = ROOT / '.github/fixtures/bun'


def expression(source: str, outputs: dict[str, str]):
    """Evaluate only the scalar expression forms present in the checked workflow."""
    source = source.strip()
    if source.startswith('${{'):
        source = source[3:-2].strip()
    source = re.sub(r'steps\.detect\.outputs\.(\w+)', lambda m: repr(outputs.get(m[1], '')), source)
    source = source.replace('&&', ' and ').replace('||', ' or ')
    if source in ('true', 'false'):
        return source == 'true'

    def resolve(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, bool)):
            return node.value
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            value = resolve(node.values[0])
            for child in node.values[1:]:
                if (isinstance(node.op, ast.And) and not value) or (isinstance(node.op, ast.Or) and value):
                    return value
                value = resolve(child)
            return value
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = resolve(node.left), resolve(node.comparators[0])
            if isinstance(node.ops[0], ast.Eq):
                return left == right
            if isinstance(node.ops[0], ast.NotEq):
                return left != right
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'format' and not node.keywords):
            template, *values = [resolve(arg) for arg in node.args]
            return template.format(*values)
        raise ValueError('Unsupported workflow expression')

    return resolve(ast.parse(source, mode='eval').body)


def configuration() -> tuple[list[dict], dict]:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    steps = workflow['jobs']['build']['steps']
    fixture_workflow = yaml.safe_load((ROOT / '.github/workflows/bun-workflow-fixtures.yml').read_text())
    actual_actions = {step['uses'] for step in fixture_workflow['jobs']['fixture']['steps'] if 'uses' in step}
    node = next(step for step in steps if step.get('uses', '').startswith('actions/setup-node@'))
    bun = next(step for step in steps if step.get('uses', '').startswith('oven-sh/setup-bun@'))
    assert node['uses'] in actual_actions and bun['uses'] in actual_actions, 'Fixture setup action differs from template'
    return steps, {'node': node, 'bun': bun}


def new_fixture(kind: str, parent: Path) -> Path:
    directory = Path(tempfile.mkdtemp(prefix='prawn-bun-' + kind + '-', dir=parent))
    shutil.copytree(FIXTURES / 'common', directory, dirs_exist_ok=True)
    shutil.copytree(FIXTURES / kind, directory, dirs_exist_ok=True)
    assert not (directory / 'node_modules').exists()
    return directory


def run_detector(steps: list[dict], directory: Path) -> dict[str, str]:
    detector = next(step for step in steps if step.get('id') == 'detect')
    output = directory / 'detector-output.txt'
    env = dict(os.environ, GITHUB_OUTPUT=str(output))
    subprocess.run(['/bin/bash', '--noprofile', '--norc', '-e', '-c', detector['run']],
                   cwd=directory, env=env, check=True, timeout=30)
    values = dict(line.split('=', 1) for line in output.read_text().splitlines())
    assert values == {'has_build': 'true', 'pm': 'bun'}, values
    return values


def prepare(kind: str, output: Path) -> Path:
    steps, actions = configuration()
    directory = new_fixture(kind, Path(os.environ.get('RUNNER_TEMP', tempfile.gettempdir())))
    values = run_detector(steps, directory)
    for action in actions.values():
        assert expression(action['if'], values), 'Template setup action is skipped'
    node, bun = actions['node']['with'], actions['bun']['with']
    cache = expression(node['cache'], values)
    automatic = expression(node.get('package-manager-cache', 'true'), values)
    assert cache == '' and automatic is False, 'Bun must not enter a setup-node cache path'
    setup = {'directory': str(directory), 'node-version': node['node-version'], 'node-cache': cache,
             'node-auto-cache': str(automatic).lower(), 'bun-version': bun['bun-version']}
    marker = {'format': kind, 'workflow_sha256': sha256(WORKFLOW.read_bytes()).hexdigest(),
              'detector': values, 'setup_inputs': setup}
    (directory / 'prepared.json').write_text(json.dumps(marker, indent=2) + '\n')
    with output.open('a') as stream:
        for key, value in setup.items():
            assert '\n' not in value and '\r' not in value
            stream.write(f'{key}={value}\n')
    return directory


def invoke(command: str, directory: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    argv = shlex.split(command)
    assert argv and argv[0] == 'bun', 'Expected a Bun command'
    argv[0] = shutil.which('bun') or 'bun'
    return subprocess.run(argv, cwd=directory, env=env, text=True, capture_output=True, timeout=45)


def verify(directory: Path) -> dict:
    directory = directory.resolve()
    parent = Path(os.environ.get('RUNNER_TEMP', tempfile.gettempdir())).resolve()
    assert directory.is_relative_to(parent) and directory.name.startswith('prawn-bun-')
    marker = json.loads((directory / 'prepared.json').read_text())
    assert marker['workflow_sha256'] == sha256(WORKFLOW.read_bytes()).hexdigest()
    steps, _ = configuration()
    active = [step for step in steps if 'run' in step and step.get('id') != 'detect'
              and expression(step.get('if', 'true'), marker['detector'])]
    install = next(step for step in active if step['name'] == 'Install dependencies (bun)')
    build = next(step for step in active if step['name'] == 'Run build')
    assert active.index(install) < active.index(build), 'Dependency install must precede build'
    install_command = install['run']
    assert shlex.split(install_command) == ['bun', 'install', '--frozen-lockfile']
    build_command = expression(build['run'], marker['detector'])
    env = dict(os.environ, npm_config_registry='http://127.0.0.1:9',
               BUN_INSTALL_CACHE_DIR=str(directory / 'isolated-cache'))
    kind = marker['format']
    lock_name = 'bun.lockb' if kind == 'legacy' else 'bun.lock'
    lock_hash = sha256((directory / lock_name).read_bytes()).hexdigest()
    assert not (directory / 'node_modules').exists()
    before = invoke(build_command, directory, env)
    assert before.returncode != 0 and 'prawn-bun-install-fixture' in before.stderr
    installed = invoke(install_command, directory, env)
    assert installed.returncode == 0, installed.stderr
    built = invoke(build_command, directory, env)
    assert built.returncode == 0, built.stderr
    assert (directory / 'artifact.txt').read_text() == 'installed dependency executed\n'
    assert sha256((directory / lock_name).read_bytes()).hexdigest() == lock_hash

    mismatch = new_fixture(kind, parent)
    extra = mismatch / 'extra-dependency'
    extra.mkdir()
    (extra / 'package.json').write_text('{"name":"extra-fixture-dependency","version":"1.0.0"}')
    package = json.loads((mismatch / 'package.json').read_text())
    package['devDependencies']['extra-fixture-dependency'] = 'file:./extra-dependency'
    (mismatch / 'package.json').write_text(json.dumps(package))
    rejected = invoke(install_command, mismatch, env)
    assert rejected.returncode != 0 and 'frozen' in rejected.stderr.lower() and 'lockfile' in rejected.stderr.lower()
    assert not (mismatch / 'artifact.txt').exists()
    assert sha256((mismatch / lock_name).read_bytes()).hexdigest() == lock_hash
    result = {'at': datetime.now(timezone.utc).isoformat(), 'format': kind,
              'workflow_sha256': marker['workflow_sha256'], 'detector': marker['detector'],
              'setup_inputs': marker['setup_inputs'], 'bun_version': subprocess.check_output(['bun', '--version'], text=True).strip(),
              'node_version': subprocess.check_output(['node', '--version'], text=True).strip(),
              'build_before_install_rejected': True, 'dependency_install_and_build_passed': True,
              'frozen_mismatch_rejected_before_build': True, 'lockfile_bytes_preserved': True,
              'application_credentials_used': False, 'dependencies': 'Synthetic local files only; registry points to closed loopback port.'}
    (directory / 'fixture-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'format': kind, 'passed': True, 'bun_version': result['bun_version']}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    setup = commands.add_parser('prepare')
    setup.add_argument('--format', choices=['legacy', 'modern'], required=True)
    setup.add_argument('--github-output', type=Path, required=True)
    run = commands.add_parser('verify')
    run.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.format, args.github_output)
    else:
        verify(args.directory)
