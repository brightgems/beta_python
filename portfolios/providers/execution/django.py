import logging
from datetime import timedelta

from django.db.models import Sum, F
from django.db.models.functions import Coalesce
from main.management.commands.rebalance import get_weights

from main.models import MarketOrderRequest, Ticker, PositionLot, ExecutionRequest
from .abstract import ExecutionProviderAbstract

logger = logging.getLogger('betasmartz.execution_provider_django')


class ExecutionProviderDjango(ExecutionProviderAbstract):
    def get_execution_request(self, reason):
        pass

    def create_market_order(self, account):
        order = MarketOrderRequest.objects.create(account=account)
        return order

    def create_execution_request(self, reason, goal, asset, volume, order, limit_price):
        return ExecutionRequest.objects.create(reason=reason, goal=goal, asset=asset, volume=volume, order=order)

    def get_asset_weights_without_tax_winners(self, goal):
        lots = PositionLot.objects \
            .filter(execution_distribution__transaction__from_goal=goal,
                    execution_distribution__execution__asset__state=Ticker.State.ACTIVE.value) \
            .annotate(ticker_id=F('execution_distribution__execution__asset__id'),
                      price=F('execution_distribution__execution__asset__unit_price'),
                      bought_price=F('execution_distribution__execution__price')) \
            .annotate(tax_gain=F('price')-F('bought_price'))\
            .values('ticker_id', 'tax_gain', 'quantity', 'price')

        lots_no_tax_gain = [lot for lot in lots if lot['tax_gain'] < 0]

        weights = get_weights(lots_no_tax_gain, goal.available_balance)
        return weights

    def get_asset_weights_held_less_than1y(self, goal, today):
        m1y = today - timedelta(days=366)
        lots = PositionLot.objects.\
            filter(execution_distribution__execution__executed__gt=m1y,
                   execution_distribution__transaction__from_goal__id=goal.id,
                   execution_distribution__execution__asset__state=Ticker.State.ACTIVE.value).\
            annotate(tid=F('execution_distribution__execution__asset__id')).values('tid').\
            annotate(value=Coalesce(Sum(F('quantity') * F('execution_distribution__execution__asset__unit_price')), 0))

        weights = dict()

        bal = goal.available_balance
        for l in lots:
            weights[l['tid']] = l['value'] / bal
        return weights
