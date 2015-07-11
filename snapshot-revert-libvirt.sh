#!/usr/bin/env bash

short_vmname="$1"
snapname="$2"


prefix=$(basename $(readlink -f .))
vmname=${prefix}_${short_vmname}

set -x
virsh snapshot-revert ${vmname} ${snapname}
