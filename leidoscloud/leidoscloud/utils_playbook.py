import os
import subprocess
import sys

from .models import *
from .settings import BASE_DIR
from .utils_host import get_current_cloud_host

# Detect if Django is being unit tested
TESTING = sys.argv[1:2] == ["test"]


# Custom exceptions
class CloudSurfAlreadyInProgressException(Exception):
    pass


class AttemptedToCloudSurfToCurrentHostException(Exception):
    pass


def move_self(target, user=None):
    # verify that there is not a current cloud surf in progress before starting
    # another. This would be shown in the transition table if there is a entry
    # without an end time.

    # Get the most recent transition and if it has not finished then
    try:
        latest_transition = Transition.objects.latest("start_time")
    except Transition.DoesNotExist:
        latest_transition = None

    # Return (and fail to run) if there is already an instance with an end time
    if latest_transition is not None:
        if not latest_transition.end_time:
            raise CloudSurfAlreadyInProgressException()

    # Ensure target is valid
    if not isinstance(target, API):
        raise ValueError("target invalid!")

    current = get_current_cloud_host()
    if current == target:
        raise AttemptedToCloudSurfToCurrentHostException()

    try:
        # Record move in model
        new_move = Transition.objects.create(
            start_provider=current, end_provider=target, user=user
        )
        new_move.save()

        # Don't run the playbook while testing!
        if TESTING:
            return

        # Bit of a hack: if get_current_cloud_host doesn't return a cloud host, ansible-playbook's path will be
        # different!
        ansible_playbook_path = (
            "ansible-playbook"
            if current.name == "none"
            else "/home/ubuntu/.local/bin/ansible-playbook"
        )

        # The pip path also changes depending on if it is running on a cloud host
        # Uses pip3 in servers, and pip on localhost.
        pip_path = "pip" if current.name == "none" else "pip3"

        main_yml_location = os.path.join(BASE_DIR, "../ansible-scripts/main.yml")

        command = [
            ansible_playbook_path,
            main_yml_location,
            "-e",
            "pip=" + pip_path,
            "-e",
            "target_host=" + target.name,
            "-e",
            "current_host=" + current.name,
        ]
        # variable needed, otherwise it won't work, even if it's not used.
        process = subprocess.Popen(command)
    except Exception as e:
        print(e)
