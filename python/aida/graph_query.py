"""
Graph query class.
"""

__author__  = "Shahzad Rajput <shahzad.rajput@nist.gov>"
__status__  = "production"
__version__ = "0.0.0.1"
__date__    = "21 January 2020"

from aida.query import Query

class GraphQuery(Query):
    """
    Graph query class.
    """

    def __init__(self, logger, query_id, predicate, object_id, sparql):
        super().__init__(logger)
        self.id = query_id
        self.predicate = predicate
        self.object_id = object_id
        self.sparql = sparql