# coding: utf-8
import os
import re
from os import getenv

import click
import envoy
import simplejson as json
import yaml
from click import ClickException


_GITLAB_CI_REMOTE_URL_PATTERN = re.compile(r'http://gitlab-ci-token:(.+)@([\.\w]+)/([-\w]+)/([-\w]+).git')


def warn(text):
    return click.style(text, fg='yellow')


def error(text):
    return click.style(text, fg='red', bold=True)


def normal(text):
    return click.style(text, fg='white')


def info(text):
    return click.style(text, fg='green')


def debug_log(fmt, *args):
    return normal(fmt % args)


def get_current_branch(cwd=None):
    """inside gitlab-ci, repo is at detached state, so you cannot get branch
    name from the current git repo, but luckily there's a environment
    variable called CI_BUILD_REF_NAME"""
    ctx = click.get_current_context()
    r = envoy.run('git rev-parse --abbrev-ref HEAD', cwd=cwd)
    if r.status_code:
        if ctx.obj['debug']:
            click.echo(debug_log('get_current_branch error: (stdout)%s, (stderr)%s', r.std_out, r.std_err))

        return ''

    branch = r.std_out.strip()
    if branch == 'HEAD':
        branch = getenv('CI_BUILD_REF_NAME', '')

    if ctx.obj['debug']:
        click.echo(debug_log('get_branch: %s', branch))

    return branch


def get_commit_hash(cwd=None):
    """拿cwd的最新的commit hash."""
    ctx = click.get_current_context()

    r = envoy.run('git rev-parse HEAD', cwd=cwd)
    if r.status_code:
        raise ClickException(r.std_err)

    commit_hash = r.std_out.strip()
    if ctx.obj['debug']:
        click.echo(debug_log('get_commit_hash: %s', commit_hash))
    return commit_hash


def get_remote_url(cwd=None, remote='origin'):
    """拿cwd的remote的url.
    发现envoy.run的command只能是bytes, 不能是unicode.
    """
    ctx = click.get_current_context()

    r = envoy.run('git remote get-url %s' % str(remote), cwd=cwd)
    if r.status_code:
        raise ClickException(r.std_err)

    remote = r.std_out.strip()

    # 对gitlab ci需要特殊处理一下
    # 丫有个特殊的格式, 不太好支持...
    match = _GITLAB_CI_REMOTE_URL_PATTERN.match(remote)
    if match:
        host = match.group(2)
        group = match.group(3)
        project = match.group(4)
        return 'git@{host}:{group}/{project}.git'.format(host=host, group=group, project=project)

    if ctx.obj['debug']:
        click.echo(debug_log('get_remote_url: %s', remote))
    return remote


def get_appname(cwd=None):
    try:
        with open(os.path.join(cwd or os.getcwd(), 'app.yaml'), 'r') as f:
            specs = yaml.load(f)
    except IOError:
        return ''
    return specs.get('appname', '')


def read_json_file(path):
    try:
        with open(path) as f:
            return json.loads(f.read())
    except (OSError, IOError):
        return None
