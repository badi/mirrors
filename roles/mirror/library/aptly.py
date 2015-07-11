#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = '''
---
module: aptly
short_description: Manage Aptly to mirror and serve repositories
options:
  action:
    description: action to execute
    required: true
    choices:
      - create
      - update
      - snapshot
      - repo
  name:
    description: name to act upon
    required: yes
  uri:
    description: a mirror from this base uri (requires use of `distribution` and `components`)
    required: when using `create`
    example: deb http://us.archive.ubuntu.com/ubuntu/ 
  distribution:
    description: the distribution portion portion of the repository
    required: when using `create`
    example: trusy
  components:
    description: the list of other components of the repository
    required: when using `create`
    example: ['main', 'restricted']
  state:
    description: indicate the desired state of the action
    choices:
      - present
      - absent
requirements:
  - https://github.com/badi/pxul.git@v2.0#egg=pxul
'''

EXAMPLES = '''
# Mirror the aptly repository
- name: Create a mirror the aptly repository
  aptly:
    action=create
    uri=http://repo.aptly.info/
    distribution=squeeze
    components=['main']
    state=present
'''

try:
    import pxul.subprocess
except ImportError:
    pxul_found = False
else:
    pxul_found = True

aptly = pxul.subprocess.Builder(['aptly'], capture='both')
gpg = pxul.subprocess.Builder(['gpg2'], capture='both')

GPGImportError = pxul.subprocess.CalledProcessError
MirrorCreateError = pxul.subprocess.CalledProcessError


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
    for existing_name, _, _ in mirror_list():
        if name == existing_name:
            return True
    return False


def gpg_import_trusted_key(keyid,
                           keyring='trustedkeys.gpg',
                           keyserver='keys.gnupg.net'):
    gpg('--no-default-keyring',
        '--keyring', keyring,
        '--keyserver', keyserver,
        '--recv-keys', keyid)


def mirror_create(name, uri, distribution, components, architectures=None):

    extra_args = []
    if architectures is not None:
        extra_args.extend(['--architectures', ','.join(architectures)])

    args = ['mirror', 'create'] + extra_args + \
           [name, uri, distribution, ' '.join(components)]

    result = aptly(*args)
    assert result.ret == 0

                       
def mirror_create_idempotent(name, *args, **kws):
    # if mirror_exists(name):
    #     return False
    # else:
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
            'trusted_key': {'required': False},
            'architectures': {'type': 'list'}
            
        },

        required_together = [
            ['uri', 'distribution', 'components', 'trusted_key']
        ],

    )

    if module.params['action'] == 'create':
        try:
            # gpg_import_trusted_key(module.params['trusted_key'])
            changed = mirror_create_idempotent(
                module.params['name'],
                module.params['uri'],
                module.params['distribution'],
                module.params['components'],
                architectures=module.params['architectures'],
            )
        except GPGImportError, e:
            module.fail_json(msg='failed to import the trusted key',
                             cmd=e.cmd, retcode=e.retcode,
                             stdout=e.stdout, stderr=e.stderr)
        except MirrorCreateError, e:
            module.fail_json(msg='failed to create the mirror',
                             cmd=e.cmd, retcode=e.retcode,
                             stdout=e.stdout, stderr=e.stderr)
        else:
            module.exit_json(changed=True)

    # elif module.params['action'] == 'update':


from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
