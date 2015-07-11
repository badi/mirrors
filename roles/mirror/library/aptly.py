#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime

try:
    import pxul.subprocess
except ImportError:
    pxul_found = False
else:
    pxul_found = True

aptly = pxul.subprocess.Builder(['aptly'], capture='both')
gpg = pxul.subprocess.Builder(['gpg2'], capture='both')


class MirrorCreateError(pxul.subprocess.CalledProcessError):
    pass


def parse_mirror_list_line(line):
    assert line.startswith('*')
    parts = line.split()
    name_dirty, uri, components = parts[1], parts[2], parts[3:]
    name = name_dirty[1:-2]  # drop the brackets and colon from [name]:
    return name, uri, components


def mirror_list():
    result = aptly('mirror', 'list')
    for line in result.out.split('\n'):
        if line.strip().startswith('*'):
            name, repo, components = parse_mirror_list_line(line.strip())
            yield name, repo, components


def mirror_exists(name):
    try:
        aptly('mirror', 'show', name)
    except pxul.subprocess.CalledProcessError, e:
        if e.stdout.strip().endswith('mirror with name {} not found'.
                                     format(name)):
            return False
        else:
            raise
    else:
        return True


def mirror_create(name, uri, distribution, components, architectures=None):

    extra_args = []
    if architectures is not None:
        extra_args.extend(['--architectures', ','.join(architectures)])

    args = ['mirror', 'create'] + extra_args + \
           [name, uri, distribution, ' '.join(components)]

    aptly(*args)


def mirror_create_idempotent(name, *args, **kws):
    if mirror_exists(name):
        return False
    else:
        mirror_create(name, *args, **kws)
        return True


def mirror_update(name):
    aptly('mirror', 'update', name)


def last_mirror_update(name):
    lines = aptly('mirror', 'show', name).out.split('\n')
    matches = filter(lambda s: s.startswith('Last update:'),
                     lines)
    assert len(matches) == 1, len(matches)
    entry = matches[0]
    last_update = entry.split(': ')[1]

    if last_update == 'never':
        return datetime.datetime.min
    else:
        return datetime.datetime.strptime(
            last_update,
            '%Y-%m-%d %H:%M:%S %Z'
        )


def mirror_update_idempotent(name, within):
    last_update = last_mirror_update(name)
    delta = datetime.datetime.utcnow() - last_update

    if delta.total_seconds() > within:
        mirror_update(name)
        return True
    else:
        return False


def main():

    module = AnsibleModule(
        argument_spec = {
            'subject': {'required': True,
                        'choices': 'mirror snapshot'.split()},
            'verb': {'required': False},
            'name': {'required': True},
            'within': {'required': False,
                       'type': 'int',
                       'default': 0},

            'uri': {'required': False},
            'distribution': {'required': False},
            'components': {'type': 'list',
                           'required': False},
            'architectures': {'type': 'list'}
            
        },

        required_together = [
            ['subject', 'verb'],
            ['uri', 'distribution', 'components']
        ],

    )

    if module.params['subject'] == 'mirror':
        if module.params['verb'] == 'create':
            try:
                changed = mirror_create_idempotent(
                    module.params['name'],
                    module.params['uri'],
                    module.params['distribution'],
                    module.params['components'],
                    architectures=module.params['architectures'],
                )
            except pxul.subprocess.CalledProcessError, e:
                module.fail_json(msg='failed to create the mirror',
                                 cmd=e.cmd, retcode=e.retcode,
                                 stdout=e.stdout, stderr=e.stderr)
            except Exception, e:
                module.fail_json(msg='Failure {}'.format(e), traceback=traceback.format_exc())
            else:
                module.exit_json(changed=changed)

        elif module.params['verb'] == 'update':
            # aptly mirror update <name>
            try:
                changed = mirror_update_idempotent(
                    module.params['name'],
                    module.params['within'])
            except pxul.subprocess.CalledProcessError, e:
                module.fail_json(msg='failed to update the mirror',
                                 cmd=e.cmd, retcode=e.retcode,
                                 stdout=e.stdout, stderr=e.stderr)
            except Exception, e:
                module.fail_json(msg='Failure {}'.format(e), traceback=traceback.format_exc())
            else:
                module.exit_json(changed=changed)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
