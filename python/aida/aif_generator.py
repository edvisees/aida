"""
AIDA AIF generator.
"""

__author__  = "Shahzad Rajput <shahzad.rajput@nist.gov>"
__status__  = "production"
__version__ = "0.0.0.1"
__date__    = "7 February 2019"

from aida.object import Object
from aida.utility import get_md5_from_string
from collections import defaultdict
from rdflib import Graph
from re import compile
from re import findall

SYSTEM_NAME = 'ldc:LDCModelGenerator'

def patch(serialized_output):
    """
    Applies patch to the serialized output, and returns the updated string.
    """
    print('--patching output')
    # apply patch to year in the output
    patched_output = serialized_output.replace('-01-01"^^xsd:gYear', '"^^xsd:gYear')
    # apply patch to xsd:double in the output
    pattern = compile('XSD_DOUBLE\((.*?)\)')
    double_values = {}
    for (double_val) in findall(pattern, patched_output):
        double_values[double_val] = 1
    for double_val in double_values:
        str_to_replace = '"XSD_DOUBLE({double_val})"'.format(double_val=double_val)
        str_to_replace_by = '"{double_val}"^^xsd:double'.format(double_val=double_val)
        patched_output = patched_output.replace(str_to_replace, str_to_replace_by)
    return patched_output

def generate_cluster_membership_triples(node, mention):
    """
    Generate the cluster membership triples.

    Parameters:
        node (aida.Node)
        mention (aida.Mention)

    The return value is a dictionary object containing triples corresponding to each document, and
    one for 'all_docs'. Those corresponding to a particular document are used for generating
    task1 document specific kbs.
    """
    mention_id = mention.get('ID')
    cluster_membership_md5 = get_md5_from_string('{node_name}:{mention_id}'.format(node_name = node.get('name'),
                                                                                     mention_id = mention_id))
    triples = """\
        _:bcm-{cluster_membership_md5} a aida:ClusterMembership .
        _:bcm-{cluster_membership_md5} aida:cluster ldc:cluster-{node_name} .
        _:bcm-{cluster_membership_md5} aida:clusterMember ldc:{mention_id} .
        _:bcm-{cluster_membership_md5} aida:confidence _:bcm-{cluster_membership_md5}-confidence .
        _:bcm-{cluster_membership_md5}-confidence a aida:Confidence .
        _:bcm-{cluster_membership_md5}-confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
        _:bcm-{cluster_membership_md5}-confidence aida:system {system} .
        _:bcm-{cluster_membership_md5} aida:system {system} .
    """.format(cluster_membership_md5 = cluster_membership_md5,
               node_name = node.get('name'),
               mention_id = mention_id,
               system = SYSTEM_NAME)

    triple_block_dict = {}
    triple_block_dict['all_docs'] = triples
    document_ids = {document_span.get('document_id'):1 for document_span in mention.get('document_spans').values()}
    for document_id in document_ids:
        triple_block_dict[document_id] = triples
    return triple_block_dict

def generate_cluster_triples(reference_kb_id, node):
    """
    Generate the cluster triples.

    Parameters:
        reference_kb_id (str)
        node (aida.Node)

    The return value is a dictionary object containing triples corresponding to each document, and
    one for 'all_docs'. Those corresponding to a particular document are used for generating
    task1 document specific kbs.
    """
    prototype = node.get('prototype')
    node_ids = []
    node_id_or_node_ids = node.get('ID')
    for node_id in node_id_or_node_ids.split('|'):
        if not node_id.startswith('NIL'):
            node_ids.append(node_id)
    link_assertion_triples = []
    for node_id in node_ids:
        triples = """\
            ldc:cluster-{node_name} aida:link _:blinkassertion{node_id} .
            _:blinkassertion{node_id} a aida:LinkAssertion .
            _:blinkassertion{node_id} aida:linkTarget "{reference_kb_id}:{node_id}" .
            _:blinkassertion{node_id} aida:system {system} .
            _:blinkassertion{node_id} aida:confidence _:blinkassertion{node_id}-confidence .
            _:blinkassertion{node_id}-confidence a aida:Confidence .
            _:blinkassertion{node_id}-confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
            _:blinkassertion{node_id}-confidence aida:system {system} .
        """.format(node_name = node.get('name'),
                   reference_kb_id = reference_kb_id,
                   node_id = node_id,
                   system = SYSTEM_NAME
                   )
        link_assertion_triples.append(triples)
    
    # generate prototype informative justifications mention spans
    informative_justification_mention_spans = node.get('informative_justification_mention_spans')
    informative_justification_triples_by_document = defaultdict(list)
    prototype_by_document = {}
    for mention_span in informative_justification_mention_spans.values():
        mention = mention_span.get('mention')
        if mention.is_negated():
            continue
        span = mention_span.get('span')
        triple = 'ldc:prototype-{node_name} aida:informativeJustification _:b{span_md5} .'.format(node_name=node.get('name'),
                                                                                               span_md5=span.get('md5'))
        informative_justification_triples_by_document['all_docs'].append(triple)
        informative_justification_triples_by_document[span.get('document_id')].append(triple)
        prototype_by_document[span.get('document_id')] = mention
        if 'all_docs' not in prototype_by_document:
            prototype_by_document['all_docs'] = mention
        elif prototype_by_document['all_docs'].get('level') != 'nam' and mention.get('level') == 'nam':
            prototype_by_document['all_docs'] = mention

    triple_block_dict = {}
    for key in informative_justification_triples_by_document:
        prototype = prototype_by_document[key]
        triples = """\
            ldc:cluster-{node_name} a aida:SameAsCluster .
            ldc:cluster-{node_name} aida:prototype ldc:prototype-{node_name} .
            ldc:cluster-{node_name} aida:system {system} .
            {informative_justification_triples}
            {link_assertion_triples}
        """.format(node_name = node.get('name'),
                   informative_justification_triples = '\n'.join(informative_justification_triples_by_document[key]),
                   link_assertion_triples = '\n'.join(link_assertion_triples),
                   prototype_object_id = prototype.get('ID'),
                   system = SYSTEM_NAME,
                   node_id = node.get('ID'),
                   reference_kb_id = reference_kb_id)
        triple_block_dict[key] = triples
    return triple_block_dict

def generate_ere_object_triples(reference_kb_id, ere_object):
    """
    Generate the ERE object triples.

    Parameters:
        reference_kb_id (str)
        ere_object (aida.Mention):
            a mention corresponding to an entity, relation or an event.
    The return value is a dictionary object containing triples corresponding to each document, and
    one for 'all_docs'. Those corresponding to a particular document are used for generating
    task1 document specific kbs.
    """
    def get_ldc_time_triples(logger, date_iri, date_string, date_type, where):
        """
        Gets the LDC time triples
        """
        type_map = {
                'starton' : 'ON',
                'endon' : 'ON',
                'startbefore' : 'BEFORE',
                'endbefore' : 'BEFORE',
                'endunk' : 'UNKNOWN',
                'endafter' : 'AFTER',
                'startafter' : 'AFTER',
                'startunk' : 'UNKNOWN'
            }
        ldc_time_triples = {}
        ldc_time_triples['day'] = ''
        ldc_time_triples['month'] = ''
        ldc_time_triples['year'] = ''
        ldc_time_triples['type'] = ''
        
        if date_type is not None:
            ldc_time_triples['type'] = '{date_iri} aida:timeType "{type}" .'.format(date_iri = date_iri,
                                                                                    type = type_map[date_type])

        if date_string is not None and date_string != 'EMPTY_NA':
            pattern = compile('^(....)-(..)-(..)$')
            match = pattern.match(date_string)
            if match:
                year = match.group(1)
                month = match.group(2)
                day = match.group(3)
                if year != 'xxxx':
                    ldc_time_triples['year'] = '{date_iri} aida:year "{year}"^^xsd:gYear .'.format(date_iri = date_iri,
                                                                                                   year = year)
                if month != 'xx':
                    ldc_time_triples['month'] = '{date_iri} aida:month "--{month}"^^xsd:gMonth .'.format(date_iri = date_iri,
                                                                                                       month = month)
                if day != 'xx':
                    ldc_time_triples['day'] = '{date_iri} aida:day "---{day}"^^xsd:gDay .'.format(date_iri = date_iri,
                                                                                               day = day)
            else:
                logger.record_event('UNEXPECTED_DATE_FORMAT', date_string, where)
        return ldc_time_triples

    logger = ere_object.get('logger')
    where = ere_object.get('where')
    ere_type = ere_object.get('node_metatype').capitalize()

    # generate ldc time assertion triples
    ldc_time_assertion_triples = ''
    if ere_type in ['Event', 'Relation']:        
        # ldc start time triples
        ldc_start_time_blank_node_iri = '_:bldctime{ere_object_id}-start'.format(ere_object_id = ere_object.get('ID'))
        ldc_start_time_triples = get_ldc_time_triples(logger,
                                                      ldc_start_time_blank_node_iri,
                                                      ere_object.get('entry').get('start_date'),
                                                      ere_object.get('entry').get('start_date_type'),
                                                      where)

        ldc_start_time_triples = """\
            _:bldctime{ere_object_id} aida:start {ldc_start_time_blank_node_iri} .
            {ldc_start_time_blank_node_iri} a aida:LDCTimeComponent .
            {ldc_start_time_day_triples}
            {ldc_start_time_month_triples}
            {ldc_start_time_year_triples}
            {ldc_start_time_type_triples}
        """.format(ere_object_id = ere_object.get('ID'),
                   ldc_start_time_blank_node_iri = ldc_start_time_blank_node_iri,
                   ldc_start_time_day_triples = ldc_start_time_triples['day'],
                   ldc_start_time_month_triples = ldc_start_time_triples['month'],
                   ldc_start_time_year_triples = ldc_start_time_triples['year'],
                   ldc_start_time_type_triples = ldc_start_time_triples['type'])

        # ldc end time triples
        ldc_end_time_blank_node_iri = '_:bldctime{ere_object_id}-end'.format(ere_object_id = ere_object.get('ID'))
        ldc_end_time_triples = get_ldc_time_triples(logger,
                                                    ldc_end_time_blank_node_iri,
                                                    ere_object.get('entry').get('end_date'),
                                                    ere_object.get('entry').get('end_date_type'),
                                                    where)

        ldc_end_time_triples = """\
            _:bldctime{ere_object_id} aida:end {ldc_end_time_blank_node_iri} .
            {ldc_end_time_blank_node_iri} a aida:LDCTimeComponent .
            {ldc_end_time_day_triples}
            {ldc_end_time_month_triples}
            {ldc_end_time_year_triples}
            {ldc_end_time_type_triples}
        """.format(ere_object_id = ere_object.get('ID'),
                   ldc_end_time_blank_node_iri = ldc_end_time_blank_node_iri,
                   ldc_end_time_day_triples = ldc_end_time_triples['day'],
                   ldc_end_time_month_triples = ldc_end_time_triples['month'],
                   ldc_end_time_year_triples = ldc_end_time_triples['year'],
                   ldc_end_time_type_triples = ldc_end_time_triples['type'])

        ldc_time_assertion_triples = """\
            ldc:{ere_object_id} aida:ldcTime _:bldctime{ere_object_id} .
            _:bldctime{ere_object_id} a aida:LDCTime .
            _:bldctime{ere_object_id} aida:system {system} .
            {ldc_start_time_triples}
            {ldc_end_time_triples}
        """.format(ere_object_id = ere_object.get('ID'),
                   ldc_start_time_triples = ldc_start_time_triples,
                   ldc_end_time_triples = ldc_end_time_triples,
                   system = SYSTEM_NAME)

    # generate link assertion triples
    has_name_triple = ''
    if ere_type == 'Entity':
        text_string = ere_object.get('entry').get('text_string')
        if len(text_string) < 256 and ere_object.get('entry').get('level') == 'nam':
            has_name_triple = 'ldc:{ere_object_id} aida:hasName "{text_string}" .'.format(ere_object_id=ere_object.get('ID'),
                                                                                      text_string=text_string.replace('"', '\\"'))
    node_ids = []
    for node_id_or_node_ids in ere_object.get('nodes'):
        for node_id in node_id_or_node_ids.split('|'):
            if not node_id.startswith('NIL'):
                node_ids.append(node_id)
    link_assertion_triples = []
    for node_id in node_ids:
        triples = """\
            ldc:{ere_object_id} aida:link _:blinkassertion{node_id} .
            _:blinkassertion{node_id} a aida:LinkAssertion .
            _:blinkassertion{node_id} aida:linkTarget "{reference_kb_id}:{node_id}" .
            _:blinkassertion{node_id} aida:system {system} .
            _:blinkassertion{node_id} aida:confidence _:blinkassertion{node_id}-confidence .
            _:blinkassertion{node_id}-confidence a aida:Confidence .
            _:blinkassertion{node_id}-confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
            _:blinkassertion{node_id}-confidence aida:system {system} .
        """.format(ere_object_id = ere_object.get('ID'),
                   reference_kb_id = reference_kb_id,
                   node_id = node_id,
                   system = SYSTEM_NAME
                   )
        link_assertion_triples.append(triples)

    # generate informative justification triples
    informative_justification_spans = ere_object.get('informative_justification_spans')
    informative_justification_triples_by_document = defaultdict(list)
    for span in informative_justification_spans.values():
        triple = 'ldc:{ere_object_id} aida:informativeJustification _:b{span_md5} .'.format(ere_object_id=ere_object.get('ID'),
                                                                                               span_md5=span.get('md5'))
        informative_justification_triples_by_document['all_docs'].append(triple)
        informative_justification_triples_by_document[span.get('document_id')].append(triple)

    triple_block_dict = {}
    for key in informative_justification_triples_by_document:
        triples = """\
            ldc:{ere_object_id} a aida:{ere_type} .
            {informative_justification_triples}
            {ldc_time_assertion_triples}
            {link_assertion_triples}
            {has_name_triple}
            ldc:{ere_object_id} aida:system {system} .
        """.format(ere_object_id=ere_object.get('ID'),
                   ere_type = ere_type,
                   ldc_time_assertion_triples = ldc_time_assertion_triples,
                   informative_justification_triples = '\n'.join(informative_justification_triples_by_document[key]),
                   link_assertion_triples = '\n'.join(link_assertion_triples),
                   has_name_triple = has_name_triple,
                   system = SYSTEM_NAME,
                   )
        triple_block_dict[key] = triples
    return triple_block_dict

def generate_text_justification_triples(document_span, generate_optional_channel_attribute_flag):
    """
    Generate the text justification triples.

    Parameters:
        document_span (aida.DocumentSpan)
        generate_optional_channel_attribute_flag (bool):
            True if you would like to generate optional channel attribute, False otherwise.

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    triple_block_dict = {}
    triples = """\
        _:b{md5} a aida:TextJustification .
        _:b{md5} aida:system {system} .
        _:b{md5} aida:source '{document_element_id}' .
        _:b{md5} aida:sourceDocument '{document_id}' .
        _:b{md5} aida:startOffset '{start_x}'^^xsd:int .
        _:b{md5} aida:endOffsetInclusive '{end_x}'^^xsd:int .
        _:b{md5} aida:confidence _:b{md5}_confidence .
        _:b{md5}_confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
        _:b{md5}_confidence a aida:Confidence .
        _:b{md5}_confidence aida:system {system} .""".format(md5 = document_span.get('md5'),
                                                             system = SYSTEM_NAME,
                                                             document_id = document_span.get('document_id'),
                                                             document_element_id = document_span.get('document_element_id'),
                                                             start_x = document_span.get('span').get('start_x'),
                                                             end_x = document_span.get('span').get('end_x')
                                                             )
    triple_block_dict['all_docs'] = triples
    triple_block_dict[document_span.get('document_id')] = triples
    return triple_block_dict

def generate_image_justification_triples(document_span, generate_optional_channel_attribute_flag):
    """
    Generate the image justification triples.

    Parameters:
        document_span (aida.DocumentSpan)
        generate_optional_channel_attribute_flag (bool):
            True if you would like to generate optional channel attribute, False otherwise.

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    triple_block_dict = {}
    triples = """\
        _:b{md5} a aida:ImageJustification .
        _:b{md5} aida:system {system} .
        _:b{md5} aida:source '{document_element_id}' .
        _:b{md5} aida:sourceDocument '{document_id}' .
        _:b{md5} aida:boundingBox _:b{md5}_boundingbox .
        _:b{md5}_boundingbox a aida:BoundingBox .
        _:b{md5}_boundingbox aida:boundingBoxUpperLeftX '{start_x}'^^xsd:int .
        _:b{md5}_boundingbox aida:boundingBoxUpperLeftY '{start_y}'^^xsd:int .
        _:b{md5}_boundingbox aida:boundingBoxLowerRightX '{end_x}'^^xsd:int .
        _:b{md5}_boundingbox aida:boundingBoxLowerRightY '{end_y}'^^xsd:int .
        _:b{md5} aida:confidence _:b{md5}_confidence .
        _:b{md5}_confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
        _:b{md5}_confidence a aida:Confidence .
        _:b{md5}_confidence aida:system {system} .""".format(md5 = document_span.get('md5'),
                                                             system = SYSTEM_NAME,
                                                             document_id = document_span.get('document_id'),
                                                             document_element_id = document_span.get('document_element_id'),
                                                             start_x = document_span.get('span').get('start_x'),
                                                             start_y = document_span.get('span').get('start_y'),
                                                             end_x = document_span.get('span').get('end_x'),
                                                             end_y = document_span.get('span').get('end_y')
                                                             )
    triple_block_dict['all_docs'] = triples
    triple_block_dict[document_span.get('document_id')] = triples
    return triple_block_dict

def generate_keyframe_justification_triples(document_span, generate_optional_channel_attribute_flag):
    """
    Generate the keyframe justification triples.

    Parameters:
        document_span (aida.DocumentSpan)
        generate_optional_channel_attribute_flag (bool):
            True if you would like to generate optional channel attribute, False otherwise.

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    triple_block_dict = {}
    triples = """\
        _:b{md5} a aida:KeyFrameVideoJustification .
        _:b{md5} aida:system {system} .
        _:b{md5} aida:keyFrame '{keyframe_id}' .
        _:b{md5} aida:source '{document_element_id}' .
        _:b{md5} aida:sourceDocument '{document_id}' .
        _:b{md5} aida:boundingBox _:b{md5}_boundingbox .
        _:b{md5}_boundingbox a aida:BoundingBox .
        _:b{md5}_boundingbox aida:boundingBoxUpperLeftX '{start_x}'^^xsd:int .
        _:b{md5}_boundingbox aida:boundingBoxUpperLeftY '{start_y}'^^xsd:int .
        _:b{md5}_boundingbox aida:boundingBoxLowerRightX '{end_x}'^^xsd:int .
        _:b{md5}_boundingbox aida:boundingBoxLowerRightY '{end_y}'^^xsd:int .
        _:b{md5} aida:confidence _:b{md5}_confidence .
        _:b{md5}_confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
        _:b{md5}_confidence a aida:Confidence .
        _:b{md5}_confidence aida:system {system} .""".format(md5 = document_span.get('md5'),
                                                             system = SYSTEM_NAME,
                                                             document_id = document_span.get('document_id'),
                                                             document_element_id = document_span.get('document_element_id'),
                                                             keyframe_id = document_span.get('keyframe_id'),
                                                             start_x = document_span.get('span').get('start_x'),
                                                             start_y = document_span.get('span').get('start_y'),
                                                             end_x = document_span.get('span').get('end_x'),
                                                             end_y = document_span.get('span').get('end_y')
                                                             )
    triple_block_dict['all_docs'] = triples
    triple_block_dict[document_span.get('document_id')] = triples
    return triple_block_dict

def generate_video_justification_triples(document_span, channel, generate_optional_channel_attribute_flag):
    """
    Generate the video justification triples.

    Parameters:
        document_span (aida.DocumentSpan)
        channel (str)
        generate_optional_channel_attribute_flag (bool):
            True if you would like to generate optional channel attribute, False otherwise.

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    triple_block_dict = {}
    channel_attribute_triple = ''
    if generate_optional_channel_attribute_flag:
        channel_attribute_triple = "_:b{md5} aida:channel '{channel}' .".format(md5 = document_span.get('md5'),
                                                                              channel = channel)
    triples = """\
        _:b{md5} a aida:VideoJustification .
        {channel_attribute_triple}
        _:b{md5} aida:system {system} .
        _:b{md5} aida:source '{document_element_id}' .
        _:b{md5} aida:sourceDocument '{document_id}' .
        _:b{md5} aida:startTimestamp "XSD_DOUBLE({start_x})" .
        _:b{md5} aida:endTimestamp "XSD_DOUBLE({end_x})" .
        _:b{md5} aida:confidence _:b{md5}_confidence .
        _:b{md5}_confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
        _:b{md5}_confidence a aida:Confidence .
        _:b{md5}_confidence aida:system {system} .""".format(md5 = document_span.get('md5'),
                                                             channel_attribute_triple = channel_attribute_triple,
                                                             system = SYSTEM_NAME,
                                                             document_id = document_span.get('document_id'),
                                                             document_element_id = document_span.get('document_element_id'),
                                                             start_x = document_span.get('span').get('start_x'),
                                                             end_x = document_span.get('span').get('end_x')
                                                             )
    triple_block_dict['all_docs'] = triples
    triple_block_dict[document_span.get('document_id')] = triples
    return triple_block_dict

def generate_picture_channel_video_justification_triples(document_span, generate_optional_channel_attribute_flag):
    """
    Generate the picture channel video justification triples.

    Parameters:
        document_span (aida.DocumentSpan)
        generate_optional_channel_attribute_flag (bool):
            True if you would like to generate optional channel attribute, False otherwise.

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    return generate_video_justification_triples(document_span, 'picture', generate_optional_channel_attribute_flag)

def generate_sound_channel_video_justification_triples(document_span, generate_optional_channel_attribute_flag):
    """
    Generate the video channel video justification triples.

    Parameters:
        document_span (aida.DocumentSpan)
        generate_optional_channel_attribute_flag (bool):
            True if you would like to generate optional channel attribute, False otherwise.

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    return generate_video_justification_triples(document_span, 'sound', generate_optional_channel_attribute_flag)

def generate_both_channels_video_justification_triples(document_span, generate_optional_channel_attribute_flag):
    """
    Generate triples for justification drawn from both channels of a video.

    Parameters:
        document_span (aida.DocumentSpan)
        generate_optional_channel_attribute_flag (bool):
            True if you would like to generate optional channel attribute, False otherwise.

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    return generate_video_justification_triples(document_span, 'both', generate_optional_channel_attribute_flag)

def generate_picture_justification_triples(document_span):
    """
    Generate the picture justification triples.

    Parameters:
        document_span (aida.DocumentSpan)

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    triple_block_dict = {}
    triples = """\
        _:b{md5} a aida:PictureChannelVideoJustification .
        _:b{md5} aida:system {system} .
        _:b{md5} aida:source '{document_element_id}' .
        _:b{md5} aida:sourceDocument '{document_id}' .
        _:b{md5} aida:startTimestamp "XSD_DOUBLE({start_x})" .
        _:b{md5} aida:endTimestamp "XSD_DOUBLE({end_x})" .
        _:b{md5} aida:confidence _:b{md5}_confidence .
        _:b{md5}_confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
        _:b{md5}_confidence a aida:Confidence .
        _:b{md5}_confidence aida:system {system} .""".format(md5 = document_span.get('md5'),
                                                             system = SYSTEM_NAME,
                                                             document_id = document_span.get('document_id'),
                                                             document_element_id = document_span.get('document_element_id'),
                                                             start_x = document_span.get('span').get('start_x'),
                                                             end_x = document_span.get('span').get('end_x')
                                                             )
    triple_block_dict['all_docs'] = triples
    triple_block_dict[document_span.get('document_id')] = triples
    return triple_block_dict

def generate_sound_justification_triples(document_span):
    """
    Generate the sound justification triples.

    Parameters:
        document_span (aida.DocumentSpan)

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    triple_block_dict = {}
    triples = """\
        _:b{md5} a aida:SoundChannelVideoJustification .
        _:b{md5} aida:system {system} .
        _:b{md5} aida:source '{document_element_id}' .
        _:b{md5} aida:sourceDocument '{document_id}' .
        _:b{md5} aida:startTimestamp "XSD_DOUBLE({start_x})" .
        _:b{md5} aida:endTimestamp "XSD_DOUBLE({end_x})" .
        _:b{md5} aida:confidence _:b{md5}_confidence .
        _:b{md5}_confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
        _:b{md5}_confidence a aida:Confidence .
        _:b{md5}_confidence aida:system {system} .""".format(md5 = document_span.get('md5'),
                                                             system = SYSTEM_NAME,
                                                             document_id = document_span.get('document_id'),
                                                             document_element_id = document_span.get('document_element_id'),
                                                             start_x = document_span.get('span').get('start_x'),
                                                             end_x = document_span.get('span').get('end_x')
                                                             )
    triple_block_dict['all_docs'] = triples
    triple_block_dict[document_span.get('document_id')] = triples
    return triple_block_dict

def generate_type_assertion_triples(mention, node_name=None):
    """
    Generate the type assertion triples.

    Parameters:
        mention (aida.Mention)
        node_name (str or None):
            node_name is provided if the mention for which the type assertion is to be
            generated is for the prototype of a cluster

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    full_type = mention.get('full_type')
    ID = mention.get('ID') if node_name is None else node_name
    subject = mention.get('ID') if node_name is None else 'prototype-{}'.format(node_name)
    type_assertion_md5 = get_md5_from_string('{ID}:{full_type}'.format(ID=ID,
                                                                  full_type=full_type
                                                                  ))

    # all_docs triple block
    justified_by_triples_by_document = defaultdict(list)
    for document_span in mention.get('document_spans').values():
        justified_by_triple = 'ldc:assertion-{type_assertion_md5} aida:justifiedBy _:b{document_span_md5} .'.format(type_assertion_md5=type_assertion_md5,
                                                                                                         document_span_md5=document_span.get('md5'))
        justified_by_triples_by_document[document_span.get('document_id')].append(justified_by_triple)
        justified_by_triples_by_document['all_docs'].append(justified_by_triple)

    # document specific triple block
    justified_by_triples = []
    triple_block_dict = {}
    for document_id in justified_by_triples_by_document:
        justified_by_triples = justified_by_triples_by_document[document_id]
        triples = """\
            ldc:assertion-{type_assertion_md5} a rdf:Statement .
            ldc:assertion-{type_assertion_md5} rdf:object ldcOnt:{full_type} .
            ldc:assertion-{type_assertion_md5} rdf:predicate rdf:type .
            ldc:assertion-{type_assertion_md5} rdf:subject ldc:{subject} .
            ldc:assertion-{type_assertion_md5} aida:confidence _:bta{type_assertion_md5}-confidence .
            _:bta{type_assertion_md5}-confidence a aida:Confidence .
            _:bta{type_assertion_md5}-confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
            _:bta{type_assertion_md5}-confidence aida:system {system} .
            {justified_by_triples}
            ldc:assertion-{type_assertion_md5} aida:system {system} .
            """.format(type_assertion_md5 = type_assertion_md5,
                       full_type = full_type,
                       subject = subject,
                       system = SYSTEM_NAME,
                       justified_by_triples = '\n'.join(justified_by_triples)
                       )
        triple_block_dict[document_id] = triples
    return triple_block_dict

def generate_argument_assertions_with_single_contained_justification_triple(slot, subject_node=None):
    """
    Generate the argument assertion triples with a single contained justification.

    Parameters:
        slot (aida.Slot)
        subject_node (aida.Node or None):
            aida.Node if the slot represents an edge between prototypes

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    subject_mention_id = slot.get('subject').get('ID')
    arguments = [slot.get('argument')]
    if subject_node is not None:
        subject_mention_id = 'prototype-{}'.format(subject_node.get('name'))
        arguments = list(slot.get('argument').get('nodes').values())

    document_ids = {'all_docs':1}
    subject_informative_justification_spans = slot.get('subject').get('informative_justification_spans')
    predicate_justification_document_id = slot.get('subject').get('document_id')
    subject_informative_justification_span = subject_informative_justification_spans[predicate_justification_document_id]
    document_ids[predicate_justification_document_id] = 1

    for argument in arguments:
        argument_mention_id = argument.get('ID')
        if subject_node is not None:
            argument_mention_id = 'prototype-{}'.format(argument.get('name'))
            if predicate_justification_document_id not in argument.get('document_ids'):
                slot.get('logger').record_event('DEFAULT_CRITICAL_ERROR', 'Predicate justification document ID {} not in the documents from which the argument came'.format(predicate_justification_document_id))
        slot_assertion_md5 = get_md5_from_string('{}:{}:{}'.format(
                                                    subject_mention_id,
                                                    slot.get('slot_type'),
                                                    argument_mention_id))
        triple_block_dict = {}
        for key in document_ids:
            triples = """\
                ldc:assertion-{slot_assertion_md5} a rdf:Statement .
                ldc:assertion-{slot_assertion_md5} rdf:object ldc:{argument_mention_id} .
                ldc:assertion-{slot_assertion_md5} rdf:predicate ldcOnt:{slot_type} .
                ldc:assertion-{slot_assertion_md5} rdf:subject ldc:{subject_mention_id} .
                ldc:assertion-{slot_assertion_md5} aida:confidence _:bslotassertion-{slot_assertion_md5}-confidence .
                _:bslotassertion-{slot_assertion_md5}-confidence a aida:Confidence .
                _:bslotassertion-{slot_assertion_md5}-confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
                _:bslotassertion-{slot_assertion_md5}-confidence aida:system {system} .
                ldc:assertion-{slot_assertion_md5} aida:justifiedBy _:bslotassertion-{slot_assertion_md5}-justification .
                _:bslotassertion-{slot_assertion_md5}-justification a aida:CompoundJustification . 
                _:bslotassertion-{slot_assertion_md5}-justification aida:containedJustification _:b{subject_mention_md5} .
                _:bslotassertion-{slot_assertion_md5}-justification aida:confidence _:bslotassertion-{slot_assertion_md5}-justification-confidence .
                _:bslotassertion-{slot_assertion_md5}-justification-confidence a aida:Confidence .
                _:bslotassertion-{slot_assertion_md5}-justification-confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
                _:bslotassertion-{slot_assertion_md5}-justification-confidence aida:system {system} .
                _:bslotassertion-{slot_assertion_md5}-justification aida:system {system} .
                ldc:assertion-{slot_assertion_md5} aida:system {system} .
                """.format(slot_assertion_md5 = slot_assertion_md5,
                           subject_mention_id = subject_mention_id,
                           argument_mention_id = argument_mention_id,
                           slot_type = slot.get('slot_type'),
                           subject_mention_md5 = subject_informative_justification_span.get('md5'),
                           system = SYSTEM_NAME
                           )
            triple_block_dict[key] = triples
    return triple_block_dict

def generate_argument_assertions_with_two_contained_justifications_triple(slot):
    """
    Generate the argument assertion triples with up to two contained justification.

    Parameters:
        slot (aida.Slot)

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    subject = slot.get('subject')
    argument = slot.get('argument')
    subject_mention_id = subject.get('ID')
    argument_mention_id = argument.get('ID')
    slot_type = slot.get('slot_type')
    slot_assertion_md5 = get_md5_from_string('{}:{}:{}'.format(subject_mention_id, slot_type, argument_mention_id))
    subject_informative_justifications = subject.get('informative_justification_spans')
    argument_informative_justifications = argument.get('informative_justification_spans')
    for informative_justifications in [subject_informative_justifications, argument_informative_justifications]:
        if len(informative_justifications) != 1:
            slot.get('logger').record_event('UNEXPECTED_NUM_INF_JUSTIFICATIONS', slot.get_code_location())
    subject_informative_justification = list(subject_informative_justifications.values())[0]
    argument_informative_justification = list(argument_informative_justifications.values())[0]
    triples = """\
        ldc:assertion-{slot_assertion_md5} a rdf:Statement .
        ldc:assertion-{slot_assertion_md5} rdf:object ldc:{argument_mention_id} .
        ldc:assertion-{slot_assertion_md5} rdf:predicate ldcOnt:{slot_type} .
        ldc:assertion-{slot_assertion_md5} rdf:subject ldc:{subject_mention_id} .
        ldc:assertion-{slot_assertion_md5} aida:confidence _:bslotassertion-{slot_assertion_md5}-confidence .
        _:bslotassertion-{slot_assertion_md5}-confidence a aida:Confidence .
        _:bslotassertion-{slot_assertion_md5}-confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
        _:bslotassertion-{slot_assertion_md5}-confidence aida:system {system} .
        ldc:assertion-{slot_assertion_md5} aida:justifiedBy _:bslotassertion-{slot_assertion_md5}-justification .
        _:bslotassertion-{slot_assertion_md5}-justification a aida:CompoundJustification . 
        _:bslotassertion-{slot_assertion_md5}-justification aida:containedJustification _:b{subject_informative_justification_md5} .
        _:bslotassertion-{slot_assertion_md5}-justification aida:containedJustification _:b{argument_informative_justification_md5} .
        _:bslotassertion-{slot_assertion_md5}-justification aida:confidence _:bslotassertion-{slot_assertion_md5}-justification-confidence .
        _:bslotassertion-{slot_assertion_md5}-justification-confidence a aida:Confidence .
        _:bslotassertion-{slot_assertion_md5}-justification-confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
        _:bslotassertion-{slot_assertion_md5}-justification-confidence aida:system {system} .
        _:bslotassertion-{slot_assertion_md5}-justification aida:system {system} .
        ldc:assertion-{slot_assertion_md5} aida:system {system} .
        """.format(slot_assertion_md5 = slot_assertion_md5,
                   subject_mention_id = subject_mention_id,
                   argument_mention_id = argument_mention_id,
                   slot_type = slot_type,
                   subject_informative_justification_md5 = subject_informative_justification.get('md5'),
                   argument_informative_justification_md5 = argument_informative_justification.get('md5'),
                   system = SYSTEM_NAME
                   )
    return triples

def generate_audio_justification_triples(document_span, generate_optional_channel_attribute_flag):
    """
    Generate the audio justification triples with a single contained justification.

    Parameters:
        document_span (aida.DocumentSpan)
        generate_optional_channel_attribute_flag (bool):
            True if you would like to generate optional channel attribute, False otherwise.

    The return value is a dictionary object containing triples corresponding to the document
    from which the span is drawn, and one for 'all_docs'. Those corresponding to a particular
    document are used for generating task1 document specific kbs.
    """
    triple_block_dict = {}
    triples = """\
        _:b{md5} a aida:AudioJustification .
        _:b{md5} aida:system {system} .
        _:b{md5} aida:source '{document_element_id}' .
        _:b{md5} aida:sourceDocument '{document_id}' .
        _:b{md5} aida:startTimestamp "XSD_DOUBLE({start_x})" .
        _:b{md5} aida:endTimestamp "XSD_DOUBLE({end_x})" .
        _:b{md5} aida:confidence _:b{md5}_confidence .
        _:b{md5}_confidence aida:confidenceValue "XSD_DOUBLE(1.0)" .
        _:b{md5}_confidence a aida:Confidence .
        _:b{md5}_confidence aida:system {system} .""".format(md5 = document_span.get('md5'),
                                                             system = SYSTEM_NAME,
                                                             document_id = document_span.get('document_id'),
                                                             document_element_id = document_span.get('document_element_id'),
                                                             start_x = document_span.get('span').get('start_x'),
                                                             end_x = document_span.get('span').get('end_x')
                                                             )
    triple_block_dict['all_docs'] = triples
    triple_block_dict[document_span.get('document_id')] = triples
    return triple_block_dict

class AIFGenerator(Object):
    """
    The class to support AIF Generation.
    """    
    def __init__(self, logger, annotations, generate_optional_channel_attribute_flag, reference_kb_id):
        """
        Initialize the AIF generator.

        Arguments:
            logger (aida.Logger)
            annotations (aida.Annotations)
            generate_optional_channel_attribute_flag (bool)
            reference_kb_id (str)
                The reference KB ID to link the nodes to.
        """
        super().__init__(logger)
        self.annotations = annotations
        self.reference_kb_id = reference_kb_id
        self.generate_optional_channel_attribute_flag = generate_optional_channel_attribute_flag
        self.triple_blocks = defaultdict(list)
        self.generate_aif()

    def generate_aif(self):
        """
        Generate AIF.
        """
        print('--generating justifications ...')
        self.generate_justifications()
        print('--generating clusters ...')
        self.generate_clusters()
        print('--generating ere objects ...')
        self.generate_ere_objects()
        print('--generating type assertions ...')
        self.generate_type_assertions()
        print('--generating cluster memberships ...')
        self.generate_cluster_memberships()
        print('--generating argument assertions ...')
        self.generate_argument_assertions()
        print('--aif generation finished ...')

    def write_output(self, output_dir, raw=False):
        """
        Writes the output to output directory specified using the argument 'output_dir'.

        The boolean argument 'raw' will be used to control the output format. If True
        raw output would be written otherwise output would be written in turtle format.
        """
        system_triples = self.get('system_triples')
        prefix_triples = self.get('prefix_triples')
        for key in self.get('triple_blocks'):
            self.get('triple_blocks')[key].insert(0, system_triples)
            self.get('triple_blocks')[key].insert(0, prefix_triples)
            graph = '\n'.join(self.get('triple_blocks')[key])
            if raw:
                print('--using raw graph for output')
            else:
                print('--using rdflib for output')
                print("--parsing raw graph ...")
                g = Graph()
                g.parse(data=graph, format="turtle")
                graph = patch(g.serialize(format="turtle").decode('utf-8'))
            filename = '{}/{}.ttl'.format(output_dir, key)
            print('--writing to output file: {}'.format(filename))
            program_output = open(filename, 'w')
            program_output.write(graph)
            program_output.close()

    def add(self, triple_block_dict):
        """
        Store the triple_block_dict to a dictionary.
        """
        for key in triple_block_dict:
            triple_block = triple_block_dict[key]
            self.get('triple_blocks')[key].append(triple_block)

    def get_system_triples(self):
        """
        Gets the system triples.
        """
        triple_block = "ldc:LDCModelGenerator a aida:System ."
        return triple_block

    def get_prefix_triples(self):
        """
        Gets the prefix triples.
        """
        triple_block = """\
            @prefix aida:  <https://tac.nist.gov/tracks/SM-KBP/2019/ontologies/InterchangeOntology#> .
            @prefix ldc:   <https://tac.nist.gov/tracks/SM-KBP/2019/ontologies/LdcAnnotations#> .
            @prefix ldcOnt: <https://tac.nist.gov/tracks/SM-KBP/2019/ontologies/LDCOntology#> .
            @prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
        """
        return triple_block

    def generate_argument_assertions(self):
        """
        Generate all the argument assertion triples.
        """
        method_name = 'generate_argument_assertions_with_single_contained_justification_triple'
        generator = globals().get(method_name)
        for node in self.get('annotations').get('nodes').values():
            for slot_name in node.get('prototype').get('slots'):
                for slot in node.get('prototype').get('slots').get(slot_name):
                    if slot.is_negated():
                        self.get('logger').record_event('SKIPPING', 'Argument assertion for edge', 'SUBJECT={}:{}:{}=OBJECT'.format(slot.get('subject').get('ID'), slot.get('slot_type'), slot.get('argument').get('ID')), "because the slot is negated")
                        continue
                    if slot.get('subject').is_negated():
                        self.get('logger').record_event('SKIPPING', 'Argument assertion for edge', 'SUBJECT={}:{}:{}=OBJECT'.format(slot.get('subject').get('ID'), slot.get('slot_type'), slot.get('argument').get('ID')), "because the subject is negated")
                        continue
                    if slot.get('argument').is_negated():
                        self.get('logger').record_event('SKIPPING', 'Argument assertion for edge', 'SUBJECT={}:{}:{}=OBJECT'.format(slot.get('subject').get('ID'), slot.get('slot_type'), slot.get('argument').get('ID')), "because the object is negated")
                        continue
                    if len(slot.get('subject').get('nodes')) == 0:
                        slot.get('logger').record_event('SKIPPING', 'Argument assertion triples containing subject', '{}'.format(slot.get('subject').get('ID')), "because the subject mention is not found in the linking table")
                        continue
                    if len(slot.get('argument').get('nodes')) == 0:
                        slot.get('logger').record_event('SKIPPING', 'Argument assertion triples containing argument', '{}'.format(slot.get('argument').get('ID')), "because the argument mention is not found in the linking table")
                        continue
                    triple_block_dict = generator(slot)
                    self.add(triple_block_dict)
                    triple_block_dict = generator(slot, node)
                    self.add(triple_block_dict)

    def generate_ere_objects(self):
        """
        Generate all the ERE object triples corresponding to the mentions in annotations.
        """
        for node in self.get('annotations').get('nodes').values():
            for mention in node.get('mentions').values():
                if mention.is_negated():
                    self.get('logger').record_event('SKIPPING', 'ERE object corresponding to mention', '{}'.format(mention.get('ID')), "because the mention is negated")
                    continue
                triple_block_dict = generate_ere_object_triples(self.get('reference_kb_id'), mention)
                self.add(triple_block_dict)

    def generate_clusters(self):
        """
        Generate all the cluster triples.
        """
        for node in self.get('annotations').get('nodes').values():
            triple_block_dict = generate_cluster_triples(self.get('reference_kb_id'), node)
            self.add(triple_block_dict)

    def generate_cluster_memberships(self):
        """
        Generate all the cluster membership triples.
        """
        for node in self.get('annotations').get('nodes').values():
            for mention in node.get('mentions').values():
                if mention.is_negated():
                    self.get('logger').record_event('SKIPPING', 'Justification triples for mention', '{}'.format(mention.get('ID')), "because the mention is negated")
                    continue
                triple_block_dict = generate_cluster_membership_triples(node, mention)
                self.add(triple_block_dict)

    def generate_justifications(self):
        """
        Generate all the justification triples.
        """
        generate_optional_channel_attribute_flag = self.get('generate_optional_channel_attribute_flag')
        for node in self.get('annotations').get('nodes').values():
            for mention in node.get('mentions').values():
                if mention.is_negated():
                    self.get('logger').record_event('SKIPPING', 'Justification triples for mention', '{}'.format(mention.get('ID')), "because the mention is negated")
                    continue
                for document_span in mention.get('document_spans').values():
                    span_type = document_span.get('span_type')
                    triple_block_dict = None
                    method_name = 'generate_{}_justification_triples'.format(span_type)
                    generator = globals().get(method_name)
                    if generator:
                        triple_block_dict = generator(document_span, generate_optional_channel_attribute_flag)
                    else:
                        self.get('logger').record_event('UNDEFINED_METHOD', method_name)
                    self.add(triple_block_dict)

    def generate_type_assertions(self):
        """
        Generate all the type assertion triples.
        """
        for node in self.get('annotations').get('nodes').values():
            for mention in node.get('mentions').values():
                if mention.is_negated():
                    self.get('logger').record_event('SKIPPING', 'Type assertion for mention', '{}'.format(mention.get('ID')), "because the mention is negated")
                    continue
                triple_block_dict = generate_type_assertion_triples(mention)
                self.add(triple_block_dict)
            for mention_type in node.get('prototype').get('types'):
                for mention in node.get('prototype').get('types').get(mention_type):
                    if mention.is_negated():
                        self.get('logger').record_event('DEFAULT_CRITICAL_ERROR', 'Negated mention encountered. Expected non-negated one.')
                    triple_block_dict = generate_type_assertion_triples(mention, node.get('name'))
                    self.add(triple_block_dict)