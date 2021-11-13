""" Commander pattern responsible for managing the execution of database operations and maintaining records (analysis) of their execution """
import time
import couchbase
import logging
from couchbase.collection import GetOptions, InsertOptions, RemoveOptions, ReplaceOptions
from couchbase.durability import ServerDurability
from couchbase.options import QueryBaseOptions
import couchbase.search as search
from datetime import timedelta

from couchbase_core.durability import Durability

DEFAULT_SCOPE = "default_scope"
DEFAULT_COLLECTION = "default_collection"
DURABILITY_MAP = {
    'low': ServerDurability(Durability.MAJORITY),
    'medium': ServerDurability(Durability.MAJORITY_AND_PERSIST_TO_ACTIVE),
    'high': ServerDurability(Durability.PERSIST_TO_MAJORITY)
}
class Operation:
    """ Operation superclass to be overridden with concrete operation types """
    def __init__(self, verbose=False, data_file_name="", cluster=None,bucket_name="",operation_type=""):
        self.data_file_name = data_file_name
        self.cluster = cluster
        self.verbose = verbose
        self.bucket_name = bucket_name
        self.set_logger(prefix=operation_type)

    def execute(self):
        pass

    def get_data_file_name(self):
        return self.data_file_name

    def debug(self, msg):
        self.logger.debug(msg, extra=self.prefix)

    def info(self, msg):
        self.logger.info(msg, extra=self.prefix)

    def error(self, msg):
        self.logger.error(msg, extra=self.prefix)

    def set_logger(self, prefix=None):
        if not prefix:
            self.prefix = {'prefix': f'Operation'}
        else:
            self.prefix = {'prefix': prefix}
        self.logger = logging.getLogger(prefix)
        self.logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(prefix)s - %(message)s')
        handler.setFormatter(formatter)
        for h in self.logger.handlers:
            self.logger.removeHandler(h)
        self.logger.addHandler(handler)

class N1QLQueryOperation(Operation):
    """ Operation representing a N1QL query execution (read) against database """
    def __init__(self, verbose=False,  data_file_name="", cluster=None,bucket_name="",vandy_phrase="vanderbilt"):
        super().__init__(
            verbose=verbose,
            data_file_name=data_file_name,
            cluster=cluster,
            bucket_name=bucket_name,
            operation_type='N1QLQuery')
        self.query = f'SELECT * FROM {self.bucket_name} WHERE vandy_phrase = "{vandy_phrase}"'
        self.opts = QueryBaseOptions(timeout=timedelta(seconds=10))
    def execute(self):
        result = self.cluster.query(self.query, self.opts)
        # self.info(result)
        return result

class GetFullDocByKeyOperation(Operation):
    """ Operation representing an operation to get a full JSON document by its key from database """
    def __init__(self, verbose=False, data_file_name="", cluster=None,bucket_name="", doc_key=0):
        super().__init__(
            verbose=verbose,
            data_file_name=data_file_name,
            cluster=cluster,
            bucket_name=bucket_name,
            operation_type='GetFullDocByKey')
        self.key = str(doc_key)
        self.bucket = bucket_name
        self.opts = GetOptions(timeout=timedelta(seconds=10))
    def execute(self):
        response = self.cluster.bucket(self.bucket_name).collection(
            DEFAULT_COLLECTION).get(self.key, self.opts)
        # self.info(response)
        return response

class FullTextSearchOperation(Operation):
    """ Operation representing a full text search (read) against database """
    def __init__(self, verbose=False, data_file_name="", cluster=None, bucket_name="", vandy_phrase="vanderbilt"):
        super().__init__(
            verbose=verbose,
            data_file_name=data_file_name,
            cluster=cluster,
            bucket_name=bucket_name,
            operation_type='FTS')
        self.query = search.QueryStringQuery(vandy_phrase)
        self.opts = search.SearchOptions(timeout=timedelta(seconds=10))
        self.index = f'default_primary_index_{bucket_name.replace("-","_")}'

    def execute(self):
        result = self.cluster.search_query(
            self.index,
            self.query,
            self.opts)
        # self.info(result)
        return result

class InsertOperation(Operation):
    """ Operation representing a document insertion into database """
    def __init__(self, verbose=False, data_file_name="", cluster=None, bucket_name="", insert_doc=None, doc_key=0,
            durability_level="low"):
        super().__init__(
            verbose=verbose,
            data_file_name=data_file_name,
            cluster=cluster,
            bucket_name=bucket_name,
            operation_type='INSERT'
            )

        self.val = insert_doc
        self.key = str(doc_key)
        self.opts = InsertOptions(timeout=timedelta(seconds=10), durability=DURABILITY_MAP[durability_level])
        # Wait for majority replication before committing - longer time

    def execute(self):
        response = None
        try:
            response = self.cluster.bucket(self.bucket_name).scope(
                DEFAULT_SCOPE
            ).collection(
                DEFAULT_COLLECTION
            ).insert(
                self.key,
                self.val,
                self.opts
            )
            # self.info(response)
        except couchbase.exceptions.DocumentExistsException as e:
            self.error(e)
        return response

class UpdateOperation(Operation):
    """ Operation representing a document update (REPLACE) in database """
    def __init__(self, verbose=False, data_file_name="", cluster=None, bucket_name="",
        doc_key=0, doc_replace_value=None, durability_level="low"):
        super().__init__(
            verbose=verbose,
            data_file_name=data_file_name,
            cluster=cluster,
            bucket_name=bucket_name,
            operation_type='UPDATE')
        self.key = str(doc_key)
        self.val = doc_replace_value
        self.opts = ReplaceOptions(timeout=timedelta(seconds=10), durability=DURABILITY_MAP[durability_level])

    def execute(self):
        response = self.cluster.bucket(self.bucket_name).scope(
            DEFAULT_SCOPE).collection(DEFAULT_COLLECTION).replace(
            self.key,
            self.val,
            self.opts
        )
        # self.info(response)
        return response

class DeleteOperation(Operation):
    """ Operation representing document deletion from database """
    def __init__(self, verbose=False, data_file_name="", cluster=None, bucket_name="", doc_key=0,
                        durability_level="low"):
        super().__init__(
            verbose=verbose,
            data_file_name=data_file_name,
            cluster=cluster,
            bucket_name=bucket_name,
            operation_type="DELETE")
        self.key = str(doc_key)
        self.opts = RemoveOptions(durability=DURABILITY_MAP[durability_level])

    def execute(self):
        response = self.cluster.bucket(self.bucket_name).scope(
            DEFAULT_SCOPE).collection(DEFAULT_COLLECTION).remove(
            self.key,
            self.opts
        )
        # self.info(response)
        return response


class OperationCommander:
    def __init__(self):
        self.n1ql_query_operations = []
        self.full_text_search_operations = []
        self.insert_operations = []
        self.delete_operations = []
        self.update_operations = []
        self.get_doc_by_key_operations = []

    def execute_operation(self, operation=None, record_operation_latency=False):
        """ Method to take in an operation (an object representing an operation to be executed) and measure the time of its execution """
        start = time.time()
        operation.execute()
        end = time.time()
        diff = end - start

        if record_operation_latency: # Save latency
            # write this latency as a new line in the operation's designated file
            with open(operation.get_data_file_name(), 'a') as f:
                f.write(f'{diff}\n')
            if isinstance(operation, N1QLQueryOperation):
                self.n1ql_query_operations.append(operation)
            elif isinstance(operation, FullTextSearchOperation):
                self.full_text_search_operations.append(operation)
            elif isinstance(operation, InsertOperation):
                self.insert_operations.append(operation)
            elif isinstance(operation, UpdateOperation):
                self.update_operations.append(operation)
            elif isinstance(operation, DeleteOperation):
                self.delete_operations.append(operation)
            elif isinstance(operation, GetFullDocByKeyOperation):
                self.get_doc_by_key_operations.append(operation)