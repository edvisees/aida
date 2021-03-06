"""
AIDA assessments class.
"""

__author__  = "Shahzad Rajput <shahzad.rajput@nist.gov>"
__status__  = "production"
__version__ = "0.0.0.1"
__date__    = "27 December 2019"

from aida.container import Container
from aida.file_handler import FileHandler
from aida.file_header import FileHeader
from aida.object import Object
import glob

assessments = {
    'ClassQuery': {
        'columns': ['queryid', 
                    'entity_type_in_query', 
                    'id', 
                    'modality', 
                    'docid', 
                    'mention_span', 
                    'assessment', 
                    'entity_type_in_response', 
                    'fqec']
        }
    }

class Assessments(Container):
    """
    AIDA assessments class.
    """
    
    def __init__(self, logger, assessments_dir, query_type):
        super().__init__(logger)
        self.assessments_dir = assessments_dir
        self.query_type = query_type
        self.load()
        
    def normalize(self, key, value):
        normalize = {'correct': 'CORRECT', 'wrong': 'INCORRECT', 'yes': 'YES', 'no': 'NO'}
        keys_to_normalize = ['assessment', 'object_linkability', 'predicate_justification_correctness']
        value = normalize[value] if key in keys_to_normalize and value in normalize else value
        return value
        
    def load(self):
        method_name = "load_{}_assessments".format(str(self.query_type).lower())
        method = self.get_method(method_name)
        if method: method()
    
    def load_classquery_assessments(self): 
        next_fqec_num = 1001
        generated_fqecs = {}
        query_type = 'ClassQuery'
        path = '{}/data/class/*/*.tab'.format(self.assessments_dir)
        header =  FileHeader(self.logger, "\t".join(assessments.get(query_type).get('columns')))   
        for filename in glob.glob(path):
            for entry in FileHandler(self.logger, filename, header):
                queryid, docid, mention_span, assessment_read, fqec_read, where = map(
                    lambda key: entry.get(key), 
                    ['queryid', 'docid', 'mention_span', 'assessment', 'fqec', 'where']
                    )
                assessment = self.normalize('assessment', assessment_read)
                query_and_document = '{}:{}'.format(queryid, docid)
                key = '{}:{}'.format(query_and_document, mention_span)
                if self.exists(key):
                    self.logger.record_event('MULTIPLE_ASSESSMENTS', key, where)
                fqec = fqec_read
                if fqec == 'NIL' and self.normalize('assessment', assessment) == 'CORRECT':
                    if key not in generated_fqecs:
                        fqec = 'NILG{}'.format(next_fqec_num)
                        generated_fqecs[key] = fqec
                    fqec = generated_fqecs[key]
                assessment_entry = Object(self.logger)
                assessment_entry.set('assessment', assessment)
                assessment_entry.set('docid', docid)
                assessment_entry.set('queryid', queryid)
                assessment_entry.set('mention_span', mention_span)
                assessment_entry.set('fqec_read', fqec_read)
                assessment_entry.set('fqec', fqec)
                assessment_entry.set('where', where)
                if not self.exists(key):
                    self.add(key=key, value=assessment_entry)
                line = 'QUERYID={} DOCID={} MENTION={} ASSESSMENT={} FQEC_READ={} FQEC={}'.format(
                    queryid, docid, mention_span, assessment, fqec_read, fqec)
                self.logger.record_event('GROUND_TRUTH', line, where)