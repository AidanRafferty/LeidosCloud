import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.db.models import CharField, F, Value

from .settings import BASE_DIR

DELETE_LOG_TXT = os.path.join(BASE_DIR, "delete_log.txt")
MAIN_LOG_TXT = os.path.join(os.path.dirname(__file__), "..", "ansible.log")


# This is heavily customized for the default population script keys that are included
# But are vital for normal operation
def are_population_script_keys_present():
    try:
        from .models import Key
        from .models import API

        # google = API.objects.filter(name="google")[0] # Commented out until we get it in the database
        aws = API.objects.filter(name="aws")[0]
        azure = API.objects.filter(name="azure")[0]
        duck = API.objects.filter(name="DuckDNS")[0]
        av = API.objects.filter(name="AlphaVantage")[0]

        # Check for duck key
        duck_token = Key.objects.get(provider=duck, name="token")
        if duck_token.value is "":
            return False

        # Check for azure keys
        azure_token = Key.objects.get(provider=azure, name="subscription_id")
        if azure_token.value is "":
            return False
        azure_token = Key.objects.get(provider=azure, name="client_id")
        if azure_token.value is "":
            return False
        azure_token = Key.objects.get(provider=azure, name="tenant")
        if azure_token.value is "":
            return False
        azure_token = Key.objects.get(provider=azure, name="secret")
        if azure_token.value is "":
            return False

        # Check for AWS keys
        aws_token = Key.objects.get(provider=aws, name="secret_key")
        if aws_token.value is "":
            return False
        aws_token = Key.objects.get(provider=aws, name="access_key")
        if aws_token.value is "":
            return False

        # Check for AlphaVantage key
        av_token = Key.objects.get(provider=av, name="key")
        if av_token.value is "":
            return False

        # If all succeed!
        return True
    except:
        # If anything goes wrong, tell the user
        return False


def get_current_cloud_host():
    """
    Retrieves the current cloud host from a specific file on the provider it's on that identifies which provider it's on
    :return:
    provider object of the host it is on
    :raise:
    ImproperlyConfigured
        Raised when the population script was not run
    """
    # Have to import here because otherwise the method is imported at the wrong time
    from .models import API

    # The contents of this file is unique on every cloud provider.
    bv_file = Path("/sys/devices/virtual/dmi/id/sys_vendor")

    file_content = ""
    if bv_file.exists():
        f = open(bv_file, "r")
        file_content = f.read()
        f.close()

    # Check if we need to run the population script by testing for Duck, our test value
    if API.objects.filter(name="DuckDNS").count() == 0:
        # we need to run the population script!
        raise ImproperlyConfigured(
            "The population script was not run, will not return current cloud host as this could have dangerous "
            "consequences "
        )

    # Create a fake column in the API field with the current contents of the sys_vendor file
    # We do this so that we can then search it for the known sys_vendor_search_strings
    cloud_host = API.objects.annotate(
        file_contents=Value(file_content, output_field=CharField())
    ).filter(file_contents__icontains=F("sys_vendor_search_string"))

    # If we found a match return it, otherwise return unknown host
    if len(cloud_host) > 0:
        return cloud_host[0]
    return API.objects.filter(name="none")[0]
