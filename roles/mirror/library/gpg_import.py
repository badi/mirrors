#!/usr/bin/python
# -*- coding: utf-8 -*-

import gnupg
import sys


def main():
    module = AnsibleModule(
        argument_spec={
            'key': {'required': True},
            'keyring': {'required': False},
            'keyserver': {'required': False},
        },
    )

    gpg = gnupg.GPG(keyring=module.params['keyring'])

    result = gpg.recv_keys(module.params['keyserver'],
                           module.params['key'])

    # handle error cases
    if not result.fingerprints:
        module.fail_json(msg='Could not import the key',
                         results=result.results,
                         reasons=result.problem_reason,
                         params=module.params
        )

    # success
    elif result.unchanged == 0:
        module.exit_json(changed=True, )
    else:  # importing keys is idempotent
        module.exit_json(changed=False)


from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
