#!/usr/bin/python
# -*- coding: utf-8 -*-

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

def main():

    module = AnsibleModule(
        argument_spec = {
            'action': {'required': True,
                       'choices': ['create', 'update', 'snapshot', 'repo']},
            'name': {'required': True},
            'uri': {'required': False},
            'distribution': {'required': False},
            'components': {'type': 'list',
                           'required': True},
            'architectures': {'type': 'list'}
            
        },

        required_together = [
            ['uri', 'distribution', 'components']
        ],

    )

    if module.params['action'] == 'create':
        try:
            changed = mirror_create_idempotent(
                module.params['name'],
                module.params['uri'],
                module.params['distribution'],
                module.params['components'],
                architectures=module.params['architectures'],
            )
        except MirrorCreateError, e:
            module.fail_json(msg='failed to create the mirror',
                             cmd=e.cmd, retcode=e.retcode,
                             stdout=e.stdout, stderr=e.stderr)
        else:
            module.exit_json(changed=changed)

    # elif module.params['action'] == 'update':


from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
