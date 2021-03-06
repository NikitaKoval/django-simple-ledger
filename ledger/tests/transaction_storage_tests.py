from django.test import TestCase
from ledger.common import SimpleTransactionStorage, Ledger, DatabaseTransactionStorage
from ledger.models import Transaction
from ledger.tests.models import TestClient, TestService, TestReason
from ledger.tests.stub import LedgerClient, LedgerService
from ledger.transactions import CreditTransaction, DepositTransaction, TRANSACTION_DEPOSIT, TRANSACTION_CREDIT
from django.contrib.contenttypes.models import ContentType


class TestTransactionSimpleStorage(TestCase):
    def setUp(self):
        self.client = LedgerClient("Azamat")
        self.service_provider = LedgerService("Dentist")

    def _create_transaction(self, klass, agent_from, agent_to, amount):
        transaction = klass()
        transaction.agent_from = agent_from
        transaction.agent_to = agent_to
        transaction.amount = amount
        return transaction

    def test_save_and_get_transactions(self):
        storage = SimpleTransactionStorage()
        ledger = Ledger()
        ledger.storage = storage
        transaction = self._create_transaction(CreditTransaction, self.client, self.service_provider, 100)
        ledger.add_transaction(transaction)
        self.assertEqual(1, len(storage.get_transactions_from(self.client)))
        self.assertEqual(1, len(storage.get_transactions_to(self.service_provider)))


class TestDatabaseStorage(TestCase):
    client = None
    service = None
    storage = None
    @classmethod
    def setUpClass(cls):
        from django.conf import settings
        settings.INSTALLED_APPS+=('ledger.tests',)
        from django.core.management import call_command
        from django.db.models import loading
        loading.cache.loaded = False
        call_command('syncdb', verbosity=0)

    def setUp(self):
        self.client = TestClient()
        self.client.name = "Azamat Tokhtaev"
        self.client.save()
        self.service = TestService()
        self.service.name = "NEO Service"
        self.service.save()
        self.storage = DatabaseTransactionStorage()

    def test_save_transaction_to_db(self):

        deposit_transaction = DepositTransaction()
        deposit_transaction.agent_from = self.client
        deposit_transaction.agent_to = self.service
        deposit_transaction.amount = 200
        deposit_transaction.batch_id = 'custom_batch_id'

        self.storage.save_transaction(deposit_transaction)

        db_transaction = Transaction.objects.get(agent_from_id=self.client.pk, agent_from_content_type=ContentType.objects.get_for_model(self.client))

        self.assertEqual(db_transaction.agent_from, self.client)
        self.assertEqual(db_transaction.agent_to, self.service)
        self.assertEqual(1, len(self.storage.get_transactions_from(self.client)))
        self.assertEqual(1, len(self.storage.get_transactions_to(self.service)))

    def test_get_deposit_transactions(self):
        deposit_transaction = DepositTransaction()
        deposit_transaction.agent_from = self.client
        deposit_transaction.agent_to = self.service
        deposit_transaction.amount = 1000
        deposit_transaction.batch_id = 'custom_batch_id'
        self.storage.save_transaction(deposit_transaction)
        transaction = self.storage.filter(self.storage.get_transactions_from(self.client), TRANSACTION_DEPOSIT)[0]
        self.assertEqual(1000, transaction.amount)

    def test_sum(self):
        deposit_transaction = DepositTransaction()
        deposit_transaction.agent_from = self.client
        deposit_transaction.agent_to = self.service
        deposit_transaction.amount = 1000
        deposit_transaction.batch_id = 'custom_batch_id'
        self.storage.save_transaction(deposit_transaction)

        deposit_transaction = DepositTransaction()
        deposit_transaction.agent_from = self.client
        deposit_transaction.agent_to = self.service
        deposit_transaction.amount = 200
        deposit_transaction.batch_id = 'custom_batch_id'
        self.storage.save_transaction(deposit_transaction)

        sum_amount = self.storage.sum(self.storage.filter(self.storage.get_transactions_from(self.client), TRANSACTION_DEPOSIT))
        self.assertEqual(1200, sum_amount)

    def test_transaction_reason(self):
        credit_transaction = CreditTransaction()
        credit_transaction.agent_from = self.client
        credit_transaction.agent_to = self.service
        credit_transaction.amount = 200
        credit_transaction.batch_id = 'custom_batch_id'

        reason = TestReason()
        reason.description = "Here is long and funny description object for the payment"
        reason.save()

        credit_transaction.reason = reason
        self.storage.save_transaction(credit_transaction)
        transaction = self.storage.filter(self.storage.get_transactions_from(self.client), TRANSACTION_CREDIT)[0]
        self.assertEqual(reason, transaction.reason)



