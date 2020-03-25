from .models import *


def populate():
    """
    This function will populate the database models with data required for the application to run correctly when it is
    first launched. API model instances will be created for each cloud provider and APIs needed.
    Key model instances will also be created for the APIs that they belong to and will reference
    the the API instance they belong to as a Foreign Key.
    :return: None
    """

    # create the Google cloud API model instance
    google_cloud = API.objects.get_or_create(
        name="google",
        long_name="Google Cloud",
        is_provider=True,
        ticker_symbol="GOOG",
        sys_vendor_search_string="Google",
    )[0]

    # create the Microsoft Azure API model instance
    azure = API.objects.get_or_create(
        name="azure",
        long_name="Microsoft Azure",
        is_provider=True,
        ticker_symbol="MSFT",
        sys_vendor_search_string="Microsoft",
    )[0]

    # create the Amazon Web Services model instance
    aws = API.objects.get_or_create(
        name="aws",
        long_name="Amazon Web Services",
        is_provider=True,
        ticker_symbol="AMZN",
        sys_vendor_search_string="Xen",
    )[0]

    # create the DuckDNS API model instance
    duck_dns = API.objects.get_or_create(
        name="DuckDNS", long_name="Duck DNS", is_provider=False
    )[0]

    # create the AlphaVantage API model instance
    alpha_vantage = API.objects.get_or_create(
        name="AlphaVantage", long_name="Alpha Vantage", is_provider=False
    )[0]

    # create the localhost API model instance
    localhost = API.objects.get_or_create(
        name="none", long_name="Unknown Host", is_provider=False
    )[0]

    # Key placeholders - secret key values will have to be entered manually in the django admin interface
    aws_secret = Key.objects.get_or_create(name="secret_key", provider=aws)[0]
    aws_access = Key.objects.get_or_create(name="access_key", provider=aws)[0]
    aws_secret.save()
    aws_access.save()

    azure_secret = Key.objects.get_or_create(name="secret", provider=azure)[0]
    azure_tenant = Key.objects.get_or_create(name="tenant", provider=azure)[0]
    azure_client_id = Key.objects.get_or_create(name="client_id", provider=azure)[0]
    azure_sub_id = Key.objects.get_or_create(name="subscription_id", provider=azure)[0]
    azure_secret.save()
    azure_tenant.save()
    azure_client_id.save()
    azure_sub_id.save()

    duck_token = Key.objects.get_or_create(name="token", provider=duck_dns)[0]
    duck_token.save()

    alpha_vantage_key = Key.objects.get_or_create(name="key", provider=alpha_vantage)[0]
    alpha_vantage_key.save()

    localhost.save()

    aws.save()
    google_cloud.save()
    azure.save()

    duck_dns.save()
    alpha_vantage.save()
