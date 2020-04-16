"""
Validator for values in AIDA response.
"""

__author__  = "Shahzad Rajput <shahzad.rajput@nist.gov>"
__status__  = "production"
__version__ = "0.0.0.1"
__date__    = "24 January 2020"

from aida.object import Object
from aida.span import Span
from aida.utility import types_are_compatible
from aida.utility import is_number

import os
import re

class Validator(Object):
    """
    Validator for values in AIDA response.
    """

    def __init__(self, logger):
        super().__init__(logger)

    def validate(self, responses, method_name, schema, entry, attribute):
        method = self.get_method(method_name)
        if method is None:
            self.record_event('UNDEFINED_METHOD', method_name)
        return method(responses, schema, entry, attribute)

    def validate_document_id(self, responses, schema, entry, attribute):
        document_id_in_entry = entry.get('document_id')
        if not responses.get('document_mappings').get('documents').exists(document_id_in_entry):
            self.record_event('UNKNOWN_ITEM', 'document', document_id_in_entry, entry.get('where'))
            return False
        if schema.get('task') == 'task1':
            kb_document_id = entry.get('kb_document_id')
            if document_id_in_entry != kb_document_id:
                self.record_event('UNEXPECTED_DOCUMENT', kb_document_id, document_id_in_entry, entry.get('where'))
                return False
        return True
    
    def validate_kb_document_id(self, responses, schema, entry, attribute):
        return self.validate_document_id(responses, schema, entry, attribute)
    
    def validate_entity_type_in_response(self, responses, schema, entry, attribute):
        entity_type_in_query = entry.get('query').get('entity_type')
        entity_type_in_response = entry.get('entity_type_in_response')
        expected_entity_type = '{0} or {0}.*'.format(entity_type_in_query)
        if not types_are_compatible(entity_type_in_query, entity_type_in_response):
            self.record_event('UNEXPECTED_ENTITY_TYPE', expected_entity_type, entity_type_in_response, entry.get('where'))
        return True

    def validate_entity_type_in_query(self, responses, schema, entry, attribute):
        entity_type_in_query = entry.get('query').get('entity_type')
        query_entity_type_in_response = entry.get('entity_type_in_query')
        if entity_type_in_query != query_entity_type_in_response:
            self.record_event('UNEXPECTED_ENTITY_TYPE', entity_type_in_query, query_entity_type_in_response, entry.get('where'))
        return True

    def validate_value_provenance_triple(self, responses, schema, entry, attribute):
        where = entry.get('where')
        
        provenance = entry.get(attribute.get('name'))
        if len(provenance.split(':')) != 3:
            self.record_event('INVALID_PROVENANCE_FORMAT', provenance, where)
            return False

        pattern = re.compile('^(\w+?):(\w+?):\((\d+),(\d+)\)-\((\d+),(\d+)\)$')
        match = pattern.match(provenance)
        if not match:
            self.record_event('INVALID_PROVENANCE_FORMAT', provenance, where)
            return False

        document_id = match.group(1)
        document_element_id = match.group(2)
        start_x, start_y, end_x, end_y = map(lambda id: match.group(id), [3, 4, 5, 6])
        
        # if provided, obtain keyframe_id and update document_element_id
        pattern = re.compile('^(\w*?)_(\d+)$')
        match = pattern.match(document_element_id)
        keyframe_num = match.group(2) if match else None
        document_element_id = match.group(1) if match else document_element_id
        
        # check if the document element has file extension appended to it
        # if so, report warning, and apply correction
        extensions = tuple(['.' + extension for extension in responses.get('document_mappings').get('encodings')])
        if document_element_id.endswith(extensions):
            self.record_event('ID_WITH_EXTENSION', 'document element id', document_element_id, where)
            document_element_id = os.path.splitext(document_element_id)[0]
            provenance = '{}:{}:({},{})-({},{})'.format(document_id, document_element_id, start_x, start_y, end_x, end_y)
            entry.set(attribute.get('name'), provenance)
        
        if document_id != entry.get('document_id'):
            self.record_event('MULTIPLE_DOCUMENTS', document_id, entry.get('document_id'), where)
            return False
        
        documents = responses.get('document_mappings').get('documents')
        document_elements = responses.get('document_mappings').get('document_elements')
        
        if document_id not in documents:
            self.record_event('UNKNOWN_ITEM', 'document', document_id, where)
            return False
        document = documents.get(document_id)

        if document_element_id not in document_elements:
            self.record_event('UNKNOWN_ITEM', 'document element', document_element_id, where)
            return False
        document_element = document_elements.get(document_element_id)
        
        modality = document_element.get('modality')
        if modality is None:
            self.record_event('UNKNOWN_MODALITY', document_element_id, where)
            return False
        
        keyframe_id = None
        if modality == 'video':
            if keyframe_num is None:
                self.record_event('MISSING_ITEM_WITHOUT_KEY', 'KeyFrameID', where)
                return False
            else:
                keyframe_id = '{}_{}'.format(document_element_id, keyframe_num)
                if keyframe_id not in responses.get('keyframe_boundaries'):
                    self.record_event('MISSING_ITEM_WITH_KEY', 'KeyFrameID', keyframe_id, where)
                    return False
        
        if not document.get('document_elements').exists(document_element_id):
            self.record_event('PARENT_CHILD_RELATION_FAILURE', document_element_id, document_id, where)
            return False
        
        for coordinate in [start_x, start_y, end_x, end_y]:
            if not is_number(coordinate):
                self.record_event('NOT_A_NUMBER', coordinate, where)
                return False
            if float(coordinate) < 0:
                self.record_event('NEGATIVE_NUMBER', coordinate, where)
                return False
        
        for start, end in [(start_x, end_x), (start_y, end_y)]:
            if start > end:
                self.record_event('START_BIGGER_THAN_END', start, end, provenance, where)
                return False
        
        document_element_boundary = responses.get('{}_boundaries'.format('keyframe' if modality=='video' else modality)).get(keyframe_id if modality == 'video' else document_element_id)
        span = Span(self.logger, start_x, start_y, end_x, end_y)
        if not document_element_boundary.validate(span):
            self.record_event('SPAN_OFF_BOUNDARY', span, document_element_boundary, document_element_id, where)
            return False
        
        return True
    
    def validate_confidence(self, responses, schema, entry, attribute):
        value = entry.get(attribute.get('name'))
        if schema.get('task') == 'task3' and schema.get('query_type') == 'GraphQuery' and value == 'NULL' and attribute.get('name') == 'edge_compound_justification_confidence':
            return True
        try: 
            float(value)
        except ValueError:
            entry.set(attribute.get('name'), 1)
            self.record_event('INVALID_CONFIDENCE', value, entry.get('where'))
            return False
        return True