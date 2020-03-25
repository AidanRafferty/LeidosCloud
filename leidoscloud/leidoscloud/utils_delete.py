import os
import subprocess
import threading

from .utils_host import DELETE_LOG_TXT


# For a many long annoying reasons this needs to be here.
# Gunicorn will murder the subprocess, stopping the deletion script from running
# to prevent this we must wait for the process to finish. However, doing so blocks the
# webserver, which is the opposite of ideal. To solve this, we wait for the subprocess to finish in a thread!
def thread_function(proc):
    proc.wait()


def delete_host(target):
    # Using os.system is the most efficient way to run the playbook, given that
    # Ansible's python API is private and not at all documented

    # In the future, hopefully there will be some kind of runner we can use to
    # make this a little more stable

    # Output of the ansible script will be logged to this file
    # This can be used to verify success
    new_env = os.environ.copy()
    new_env["ANSIBLE_LOG_PATH"] = DELETE_LOG_TXT

    try:
        child_proc = subprocess.Popen(
            [
                "/home/ubuntu/.local/bin/ansible-playbook",
                "/home/ubuntu/storm/ansible-scripts/death.yml",
                "-e",
                "to_delete_host='" + target.name + "'",
            ],
            env=new_env,
            shell=False,
            preexec_fn=os.setpgrp,
        )
        wait_thread = threading.Thread(target=thread_function, args=(child_proc,))
        wait_thread.start()
    except Exception as e:
        print("Failed to launch deletion script:")
        print(e)
