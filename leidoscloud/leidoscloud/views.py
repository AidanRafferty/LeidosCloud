import datetime
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.timesince import timesince
from django.views.decorators.cache import never_cache
from leidoscloud.models import Transition, API, StockData, Prediction

from . import utils_host
from . import utils_playbook


@login_required
@never_cache
def index(request):
    """
    The index view of the application.

    :param request: HTTP request object
    :return: return the rendered index page using the html template and the context dictionary for the page
    """

    # fill the context dictionary with the name of the current hostname
    context_dict = {
        "current_provider": utils_host.get_current_cloud_host().long_name,
        "running_time": None,
        "end_provider": None,
    }

    # Get time since latest start time
    try:
        # get the latest transition object
        latest_transition = Transition.objects.latest("start_time")
        # if the latest transition is still in progress
        if not latest_transition.end_time:
            # Assumes we are moving!
            # add the provider being transitioned to into the context dictionary
            context_dict["end_provider"] = latest_transition.end_provider.long_name
        # otherwise if no transition is taking place
        else:
            # set the running time to the length of time since the transition to the current host finished
            context_dict["running_time"] = timesince(
                latest_transition.end_time, timezone.now()
            )
    # if no transitions have been made
    except Transition.DoesNotExist:
        # This is the initial run of the application, display some blank info
        context_dict["running_time"] = "eternity and/or never"

    # Check all keys are present
    if not utils_host.are_population_script_keys_present():
        messages.add_message(
            request,
            messages.ERROR,
            "You don't have all necessary keys in your database. The program will not work! Please enter all needed "
            "keys in the admin page.",
        )
    return render(request, "index.html", context_dict)


@login_required
@never_cache
def cloudsurf(request):
    """
    This view represents the cloudsurf page which allows users to choose the next host to move the website to from the
    list of available cloud providers

    :param request: HTTP request object
    :return: return the rendered cloudsurf page using the html template and the context dictionary for the page
    """

    # get the list of available cloud providers
    api_list = API.objects.filter(is_provider=True)
    # add the list of available cloud providers to the context dictionary
    context_dict = {"apis": api_list}
    return render(request, "cloudsurf.html", context_dict)


@login_required
def cloudsurfing(request):
    """
    This view will be called in order to start a cloudsurf

    :param request: HTTP request object
    :return: redirect the user to the index page when the cloudsurf to a new cloud provider has been started or an
    error has occurred while attempting to start the cloudsurf.
    """

    # get the name of the cloud provider that has been chosen to be the next host of the website
    target_name = request.path.replace("/", "")
    # We can rely on this always existing because we can rely on the population script
    target = API.objects.filter(name=target_name)[0]

    try:
        # attempt to cloudsurf to the target cloud provider
        utils_playbook.move_self(
            target, user=(request.user if not request.user.is_anonymous else None)
        )
    # catch the exception thrown if there is already a cloudsurf in progress
    except utils_playbook.CloudSurfAlreadyInProgressException:
        # add a log message explaining the error that has occurred
        messages.add_message(
            request,
            messages.ERROR,
            "Failed to move to "
            + target.long_name
            + " because a CloudSurf is already in progress",
        )
        # redirect the user to the index page
        return redirect("/")

    # catch the exception that is thrown if the
    except utils_playbook.AttemptedToCloudSurfToCurrentHostException:
        # add a log message explaining the error that has occured
        messages.add_message(
            request,
            messages.ERROR,
            "Failed to move to " + target.long_name + " because it is the current host",
        )
        # redirect the user to the index page
        return redirect("/")

    # add a message to the log indicating that the cloudsurf to the target cloud provider has begun
    messages.add_message(
        request, messages.SUCCESS, "Moving to {}!".format(target.long_name)
    )

    # redirect the user to the index page
    return redirect("/")


@login_required
@never_cache
def cloudsurfing_status(request):
    """
    Analyze the main cloudsurf log to get the current status of the cloudsurf

    :param request: HTTP request object
    :return: JSON response object
    """

    response = {}
    with open(utils_host.MAIN_LOG_TXT, "rb") as fh:
        # From
        # https://stackoverflow.com/questions/3346430/what-is-the-most-efficient-way-to-get-first-and-last-line-of-a-text-file
        # Get last line of file
        try:
            fh.seek(-2500, os.SEEK_END)
        except:
            # Looks like the file is too small. Load the entire thing!
            fh.seek(os.SEEK_END, 0)
        lines = fh.readlines()
        last = lines[-1].decode()

        # If this line doesn't have a TASK, keep moving up until we do
        i = 2
        while "TASK" not in last:
            # If we see a fatal, let's show that to the user
            if "fatal" in last:
                response["error"] = last
                response[
                    "status"
                ] = "Ansible has crashed! Most likely keys have not been configured correctly. See log for details"
                return JsonResponse(response)
            try:
                last = lines[-i].decode()
            except IndexError:
                response["error"] = "Invalid ansible log. Check entire log for details"
                return JsonResponse(response)
            i += 1

        last_date = parse_datetime(last[0:18])
        response["date"] = last_date
        since_last_date = datetime.datetime.now() - last_date

        # Include the section within the brackets as the current status
        response["status"] = last[last.find("[") + 1 : last.find("]")]

        # This item is last on servers which are freshly migrated! Account for this
        if "Copying self to server" in last:
            # Could be an actual status item!
            if since_last_date > datetime.timedelta(minutes=2):
                # It's not a real logitem. Just the stuff left over!
                response["date"] = datetime.datetime.now()
                response["status"] = "Not CloudSurfing"
    # otherwise check if the line contains TASK and if so return it otherwise return one above
    return JsonResponse(response)


@login_required
@never_cache
def full_log(request):
    """
    This view will be called when the user enters the URL for the full log page for either the deletion or execution log

    :param request: HTTP request object
    :return: return the rendered full log of either the main ansible log or the deletion log using the html template
    and the context dictionary for the page
    """

    # Either open the LOG_TXT or the ansible log depending on the request path
    file_to_open = (
        utils_host.DELETE_LOG_TXT
        if "delete" in request.path
        else utils_host.MAIN_LOG_TXT
    )
    try:
        f = open(file_to_open, "r")
        log = f.read()
        f.close()
    except IOError as err:
        log = "Unavailable. Failed to open with " + str(err)

    context_dict = {
        "name": "Deletion" if "delete" in request.path else "Execution",
        "contents": log,
    }
    return render(request, "log.html", context_dict)


@login_required
def prediction(request):
    """
    This view will be called when the predictions page URL is entered which is used to offer a prediction for the next
    cloud provider that should be moved to based on providers share data.

    :param request: HTTP request object
    :return: return the rendered prediction page using the html template and the context dictionary for the page
    """

    context_dict = {}
    return render(request, "prediction.html", context_dict)
