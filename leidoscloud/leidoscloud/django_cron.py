import os

from django_cron import CronJobBase, Schedule
from django.utils import timezone
from . import utils_host
from . import utils_playbook
from . import utils_stock_api
from .models import *
from .utils_stock_api import save_stock_data, save_best_prediction
import datetime


class CheckHangingScripts(CronJobBase):
    RUN_EVERY_MINS = 30
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = "leidoscloud.hanging_script_check"  # checks if script is hanging

    def do(self):
        transition = Transition.objects.latest("start_time")
        # If there is an open transition which has not finished within an hour
        if (timezone.now() - transition.start_time) > datetime.timedelta(
            minutes=60
        ) and transition.end_time is None:
            target = transition.end_provider
            # Stop all current attempts
            os.system("killall ansible-playbook")
            # Delete the transition so move_self doesn't raise an AlreadyInProgressException
            transition.delete()
            try:
                utils_playbook.move_self(target)
                return (
                    "Attempt a move to "
                    + target.name
                    + " because previous attempt failed!"
                )
            except utils_playbook.CloudSurfAlreadyInProgressException:
                # For some reason only a valueerror gets logged
                raise ValueError(
                    "Failed to CloudSurf because a CloudSurf is already in progress!"
                )
            except Exception as e:
                return e
        else:
            return "Successfully checked for hanging scripts. None found."


class CloudSurfCron(CronJobBase):
    RUN_EVERY_MINS = 20

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = "leidoscloud.cloudsurf_cron"  # a unique code

    def do(self):
        """
        Due to the way django works, the only way to handle errors individually is to return via  a string
        This is why the below has a string check. Not ideal.
        """
        alpha, provider_objects = utils_stock_api.get_provider_api()
        if isinstance(provider_objects, str) or isinstance(alpha, str):
            # This returns any exceptions we've handled in get_provider_api
            return provider_objects
        key = utils_stock_api.get_api_key(alpha)
        stock_dict, symbols = utils_stock_api.get_cloud_target(provider_objects, key)
        # save the stock market data for the predictions table to DB
        save_stock_data(stock_dict)
        save_best_prediction()

        if isinstance(stock_dict, str):
            # This returns any exceptions we've handled in get_cloud_target
            return stock_dict

        target = utils_stock_api.process_api_json(stock_dict, symbols)
        if utils_host.get_current_cloud_host() == target:
            return "Staying put. This is the provider with the lowest loss/least gain."

        # This fires only if there is a different host to move to!
        try:
            utils_playbook.move_self(target)
            return (
                "Attempt a move to "
                + target.name
                + " because they have had the largest loss/least gain!"
            )
        except utils_playbook.CloudSurfAlreadyInProgressException:
            # For some reason only a valueerror gets logged
            raise ValueError(
                "Failed to CloudSurf because a CloudSurf is already in progress!"
            )
        except Exception as e:
            return e
