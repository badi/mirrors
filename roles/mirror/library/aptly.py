#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import pexpect as expect
from pipes import quote
from StringIO import StringIO

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


def last_change_time(lines, entryname):
    matches = filter(lambda s: s.startswith(entryname),
                     lines)
    assert len(matches) == 1, matches
    entry = matches[0]
    parts = entry.split(': ', 1)
    assert len(parts) == 2, parts
    when = parts[1]

    if when == 'never':
        return datetime.datetime.min
    else:
        return datetime.datetime.strptime(
            when,
            '%Y-%m-%d %H:%M:%S %Z'
        )


def within_window(when, within):
    delta = datetime.datetime.utcnow() - when

    if delta.total_seconds() <= within:
        return True
    else:
        return False


def mirror_update_idempotent(name, within):
    lines = aptly('mirror', 'show', name).out.split('\n')
    last_update = last_change_time(lines, 'Last update:')

    if not within_window(last_update, within):
        mirror_update(name)
        return True
    else:
        return False


def create_snapshot_name(name, time):
    time = time.isoformat()
    return '{name}_UTC-{time}'.format(**locals())


def snapshot_create(name):
    now = datetime.datetime.utcnow()
    snapname = create_snapshot_name(name, now)
    aptly('snapshot', 'create', snapname, 'from', 'mirror', name)


def snapshot_list():
    result = aptly('snapshot', '-raw', '-sort=time', 'list')
    return result.out.split('\n')


def most_recent_snapshot(name):
    for snap in reversed(snapshot_list()):
        if snap.startswith(name):
            return snap
    time = datetime.datetime.min.replace(microsecond = 1)
    return create_snapshot_name(name, time)


def snapshot_create_idempotent(name, within):

    last_snap = most_recent_snapshot(name)
    parts = last_snap.split('_', 1)
    assert len(parts) == 2, parts
    timestr = parts[1]

    last = datetime.datetime.strptime(
        timestr,
        'UTC-%Y-%m-%dT%H:%M:%S.%f'
    )

    if not within_window(last, within):
        snapshot_create(name)
        return True
    else:
        return False


def fail_subprocess(module, e, msg):
    module.fail_json(msg=msg,
                     cmd=e.cmd, retcode=e.retcode,
                     stdout=e.stdout, stderr=e.stderr)


def already_published(name):
    return name in aptly('publish', 'list').out


def publish_snapshot(name, passphrase=None):
    snapshot = most_recent_snapshot(name)
    if snapshot is None:
        raise ValueError('Snapshot not found for {}'.format(name))

    # Regular Popen.communicate or Popen.stdin.write would not work
    # correctly. My guess is that the aptly executable itself call out
    # to the gpg command and sending the input through several levels
    # does not work correctly. Using the `pexpect` api works though.

    cmdlist = ['aptly', 'publish', 'snapshot', snapshot]
    cmd = ' '.join(map(quote, cmdlist))

    output = StringIO()

    child = expect.spawn(cmd, logfile=output)

    if passphrase is not None:
        for i in xrange(2):  # there are 2 prompts for the passphrase
            child.expect('Enter passphrase:')
            child.sendline(passphrase)

    child.wait()
    child.close()  # to get the return code

    if child.exitstatus is not 0:
        raise subprocess.CalledProcessError(
            returncode=child.exitstatus,
            cmd=cmd,
            output=output.getvalue())


def publish_snapshot_idempotent(name, passphrase=None):

    if not already_published(name):
        publish_snapshot(name, passphrase=passphrase)
        return True
    else:
        return False

def main():

    module = AnsibleModule(
        argument_spec = {
            'subject': {'required': True,
                        'choices': 'mirror snapshot publish'.split()},
            'verb': {'required': False},
            'name': {'required': False},
            'within': {'required': False,
                       'type': 'int',
                       'default': 0},

            'uri': {'required': False},
            'distribution': {'required': False},
            'components': {'type': 'list',
                           'required': False},
            'architectures': {'type': 'list'},

            'gpg_passphrase': {'required': False},

        },

        required_together = [
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
                fail_subprocess(module, e, 'failed to create the mirror')
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
                fail_subprocess(module, e, 'failed to update the mirror')
            except Exception, e:
                module.fail_json(msg='Failure {}'.format(e), traceback=traceback.format_exc())
            else:
                module.exit_json(changed=changed)

    elif module.params['subject'] == 'snapshot':
        if module.params['verb'] == 'create':
            # snapshot create <name>_{timestamp} from mirror <name>
            try:
                changed = snapshot_create_idempotent(
                    module.params['name'],
                    module.params['within'])
            except pxul.subprocess.CalledProcessError, e:
                fail_subprocess(module, e, 'failed to create the snapshot')
            except Exception, e:
                module.fail_json(msg='Failure {}'.format(e),
                                 traceback=traceback.format_exc())
            else:
                module.exit_json(changed=changed)

    elif module.params['subject'] == 'publish':
        if module.params['verb'] == 'snapshot':
            # aptly snapshot publish <name>_{timestamp}
            try:
                changed = publish_snapshot_idempotent(
                    module.params['name'],
                    module.params['gpg_passphrase']
                )
            except subprocess.CalledProcessError, e:
                module.fail_json(msg='failed to publish snapshot',
                                 traceback=traceback.format_exc(),
                                 returncode=e.returncode,
                                 cmd=e.cmd,
                                 output=e.output)
            except Exception, e:
                module.fail_json(msg='Failure {}'.format(e),
                                 traceback=traceback.format_exc())
            else:
                module.exit_json(changed=changed)


from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
