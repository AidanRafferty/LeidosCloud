from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class API(models.Model):
    """
    Django Model used to store details of the APIs and cloud providers we are using

    ...
    Fields
    ------
    id : AutoField
        A unique automatically generated integer value which is the primary key of the model
    name : CharField
        the short name of the API
    long_name : CharField
        the long name of the API
    is_provider : BooleanField
        True if the model instance represents a cloud provider
    ticker_symbol : CharField
        This stores the Stock Market symbol of the provider.
        Will be null if the model instance is not for a cloud provider
    sys_vendor_search_string : CharField
        Used to identify the current host of the application.

    Methods
    -------
    __str__(self)
        a toString method that allows model instances to be represented by their long_name when printed
    """

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20)
    long_name = models.CharField(max_length=30)
    is_provider = models.BooleanField()
    ticker_symbol = models.CharField(max_length=10, null=True)
    sys_vendor_search_string = models.CharField(
        max_length=10,
        null=True,
        help_text="The current host is identified by reading /sys/devices/virtual/dmi/id/sys_vendor. Please enter a "
        "unique string which appears in this file when running on this cloud host.",
    )

    def __str__(self):
        return self.long_name


class Transition(models.Model):
    """
    Django model used to represent the transitions that have taken place between cloud providers.

    ...
    Fields
    ------
    id : AutoField
        A unique automatically generated integer value which is the primary key of the model
    user : Django User object
        User object which represents the user who initiated the transition.
        Null if the transition was initiated automatically
    start_provider : API Model object
        The API object of the cloud provider that the application was hosted on before the transition started
        This is a foreign key of the model
    end_provider : API Model object
        The API object of the cloud provider that has been transitioned to and the application is now hosted on
        This is a foreign key of the model
    start_time : DateTimeField
        The date and time that the transition was started at
    end_time : DateTimeField
        The date and time that the transition finished at
    succeeded : BooleanField
        Boolean value which is true if the transition was completed successfully, false otherwise
    deleted : BooleanField
        Boolean value which is true if the old instance of the previous cloud provider hosting the application has been
        deleted successfully, false otherwise

    Methods
    -------
    __str__(self)
        a toString method that represents transitions as a message informing that a transition has been made from the
        start_provider to the end_provider
    """

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    start_provider = models.ForeignKey(
        API,
        related_name="start_provider",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"is_provider": True},
    )
    end_provider = models.ForeignKey(
        API,
        null=True,
        related_name="end_provider",
        on_delete=models.SET_NULL,
        limit_choices_to={"is_provider": True},
    )
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True)
    succeeded = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return (
            self.start_provider.long_name
            + " to "
            + self.end_provider.long_name
            + " at "
            + str(self.start_time)
        )


class Key(models.Model):
    """
    Django Model that is used to store the details of the keys we are using and which API instance they belong to

    ...
    Fields
    ------
    id : AutoField
        A unique automatically generated integer value which is the primary key of the model
    name : CharField
        The name of the key
    value : CharField
        The value of the key itself
    provider : API Model instance
        The API model instance representing the API that the key belongs to
        This is a foreign key of the model

    Methods
    -------
    __str__(self)
        a toString method that represents keys as a message showing the name of the key and the name of the API that
        it belongs to
    """

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20)
    value = models.CharField(max_length=100)
    provider = models.ForeignKey(API, on_delete=models.CASCADE)

    def __str__(self):
        return self.name + " for " + self.provider.long_name


class StockData(models.Model):
    """
    Django Model that contains records representing the stock market readings
    of each of the 3 cloud providers at different times of day

    Fields
    ------
    id : AutoField
        A unique automatically generated integer value which is the primary key of the model
    time : DateTimeField
        DateTime entry which represents the time of the stock market reading
    google : FloatField
        A decimal value which represents percentage share price change so far in the day of trading for Google
    azure : FloatField
        A decimal value which represents percentage share price change so far in the day of trading for Microsoft
    aws : FloatField
        A decimal value which represents percentage share price change so far in the day of trading for Amazon

    Methods
    -------
    __str__(self)
        a toString method that represents StockData entries as a message listing the names of each of the companies
        and their respective field values
    """

    id = models.AutoField(primary_key=True)
    time = models.DateTimeField(default=timezone.now)
    google = models.FloatField()
    azure = models.FloatField()
    aws = models.FloatField()

    def __str__(self):
        return (
            "google = "
            + str(self.google)
            + " azure = "
            + str(self.azure)
            + " aws = "
            + str(self.aws)
        )


class Prediction(models.Model):
    """
    Django Model that contains predictions for the cloud provider that should be moved to next based on stock market
    data readings

    Fields
    ------
    id : AutoField
        A unique automatically generated integer value which is the primary key of the model
    time : DateTimeField
        The time that the prediction was made
    provider : API Model instance
        The API model instance representing the provider that has been predicted to be the best to move to next
        This is a foreign key of the model
    Methods
    -------
    __str__(self)
        a toString method that represents Prediction objects as a message indicating the prediction is the name of the
        provider in the prediction object
    """

    id = models.AutoField(primary_key=True)
    time = models.DateTimeField()
    provider = models.ForeignKey(
        API,
        related_name="provider",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"is_provider": True},
    )

    def __str__(self):
        return "The prediction is " + self.provider.name
