from rest_framework import serializers

from api.v1.serializers import (NoCreateModelSerializer,
                                NoUpdateModelSerializer,
                                ReadOnlyModelSerializer)
from client.models import ClientAccount, AccountBeneficiary
import logging
from user.models import SecurityAnswer

logger = logging.getLogger('api.v1.account.serializers')


class AccountBeneficiarySerializer(ReadOnlyModelSerializer):
    class Meta:
        model = AccountBeneficiary


class AccountBeneficiaryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountBeneficiary
        fields = (
            'type',
            'name',
            'relationship',
            'birthdate',
            'share',
        )


class AccountBeneficiaryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountBeneficiary
        fields = (
            'type',
            'name',
            'relationship',
            'birthdate',
            'share',
            'account',
        )


class ClientAccountSerializer(ReadOnlyModelSerializer):
    """
    Read-only ClientAccount Serializer
    """

    class Meta:
        model = ClientAccount


class ClientAccountCreateSerializer(NoUpdateModelSerializer):
    """
    When creating an account via the API, we want the name to be required,
    so enforce it.
    """
    account_name = serializers.CharField(max_length=255, required=True)

    class Meta:
        model = ClientAccount
        fields = (
            'account_type',
            'account_name',
            'account_number',
            'primary_owner',
        )

    def create(self, validated_data):
        ps = validated_data['primary_owner'].advisor.default_portfolio_set
        validated_data.update({
            'default_portfolio_set': ps,
        })
        return (super(ClientAccountCreateSerializer, self)
                .create(validated_data))


class ClientAccountUpdateSerializer(NoCreateModelSerializer):
    """
    Updatable ClientAccount Serializer
    """
    question_one = serializers.IntegerField(required=True)
    answer_one = serializers.CharField(required=True)
    question_two = serializers.IntegerField(required=True)
    answer_two = serializers.CharField(required=True)

    class Meta:
        model = ClientAccount
        fields = (
            'account_name',
            'tax_loss_harvesting_status',

            'question_one',
            'answer_one',
            'question_two',
            'answer_two',
        )

    def validate(self, data):
        request = self.context.get('request')
        user = request.user
        # no user is create request for initial registration

        # SecurityAnswer checks
        if data.get('question_one') == data.get('question_two'):
            logger.error('ClientAccountUpdateSerializer given matching questions %s' % data.get('question_one'))
            raise serializers.ValidationError({'question_two': 'Questions must be unique'})

        try:
            sa1 = SecurityAnswer.objects.get(pk=data.get('question_one'))
            if sa1.user != user:
                logger.error('SecurityAnswer not found for user %s and question %s with ClientAccountUpdateSerializer' % (user.email, data.get('question_one')))
                raise serializers.ValidationError({'question_one': 'User does not own given question'})
        except:
            logger.error('ClientAccountUpdateSerializer question %s not found' % data.get('question_one'))
            raise serializers.ValidationError({'question_one': 'Question not found'})

        if not sa1.check_answer(data.get('answer_one')):
            logger.error('ClientAccountUpdateSerializer answer two was wrong')
            raise serializers.ValidationError({'answer_one': 'Wrong answer'})

        try:
            sa2 = SecurityAnswer.objects.get(pk=data.get('question_two'))
            if sa2.user != user:
                logger.error('SecurityAnswer not found for user %s and question %s with ClientAccountUpdateSerializer' % (user.email, data.get('question_two')))
                raise serializers.ValidationError({'question_two': 'User does not own given question'})
        except:
            logger.error('ClientAccountUpdateSerializer question %s not found' % data.get('question_two'))
            raise serializers.ValidationError({'question_two': 'Question not found'})

        if not sa2.check_answer(data.get('answer_two')):
            logger.error('ClientAccountUpdateSerializer answer two was wrong')
            raise serializers.ValidationError({'answer_two': 'Wrong answer'})

        return data
