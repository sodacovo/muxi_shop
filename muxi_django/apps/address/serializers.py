
from rest_framework import serializers

from address.models import UserAddress
from django.conf import settings


class AddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserAddress
        fields = '__all__'