#!/usr/bin/perl
use strict;

use TranslateAnnotationsManagerLib;

my $TOPIC = shift;
$TOPIC = "T101" unless $TOPIC; 

my $annotations_dir = "data/LDC2018E45_AIDA_Scenario_1_Seedling_Annotation_V3.0";

my ($filename, $filehandler, $header, $entries, $i);

my %mappings;

# Load parent children DOCID mapping from parent_children.tab
my $documents = Documents->new();
my $documentelements = DocumentElements->new();

$filename = "data/LDC2018E01_AIDA_Seedling_Corpus_V1/docs/parent_children.tab";
$filehandler = FileHandler->new($filename);
$header = $filehandler->get("HEADER");
$entries = $filehandler->get("ENTRIES");
$i=0;
foreach my $entry( $entries->toarray() ){
  $i++;
  #print "ENTRY # $i:\n", $entry->tostring(), "\n";
  my $document_id = $entry->get("parent_uid");
  my ($document_eid) = split(/\./, $entry->get("child_file"));
  my $detype = $entry->get("dtyp");
  
  my $document = $documents->get("BY_KEY", $document_id);
  $document->set("DOCUMENTID", $document_id);
  my $documentelement = DocumentElement->new();
  $documentelement->set("DOCUMENT", $document);
  $documentelement->set("DOCUMENTID", $document_id);
  $documentelement->set("DOCUMENTELEMENTID", $document_eid);
  $documentelement->set("TYPE", $detype);
  
  $document->add_document_element($documentelement);
  $documentelements->add($documentelement, $document_eid) unless $document_eid eq "n/a";
}

# Load parent children DOCID mapping from uid_info_v2.tab

$filename = "data/LDC2018E01_AIDA_Seedling_Corpus_V1/docs/uid_info_v2.tab";
$filehandler = FileHandler->new($filename);
$header = $filehandler->get("HEADER");
$entries = $filehandler->get("ENTRIES");
$i=0;
foreach my $entry( $entries->toarray() ){
  $i++;
  #print "ENTRY # $i:\n", $entry->tostring(), "\n";
  my $document_id = $entry->get("uid");
  my ($document_eid) = split(/\./, $entry->get("derived_uid"));
  
  my $document = $documents->get("BY_KEY", $document_id);
  $document->set("DOCUMENTID", $document_id);
  my $documentelement = DocumentElement->new();
  $documentelement->set("DOCUMENT", $document);
  $documentelement->set("DOCUMENTID", $document_id);
  $documentelement->set("DOCUMENTELEMENTID", $document_eid) unless $document_eid eq "n/a";
  $documentelement->set("TYPE", "txt");
  
  $document->add_document_element($documentelement) unless $document_eid eq "n/a";
  $documentelements->add($documentelement, $document_eid) unless $document_eid eq "n/a";
}

# Load role mappings

my (%role_mapping, %event_relation_type_mapping);
$filename = "data/nist-role-mapping-compact-20180618.txt";
$filehandler = FileHandler->new($filename);
$header = $filehandler->get("HEADER");
$entries = $filehandler->get("ENTRIES");
$i=0;
foreach my $entry( $entries->toarray() ){
  $i++;
  #print "ENTRY # $i:\n", $entry->tostring(), "\n";
  my $ldc_type = $entry->get("ldctype");
  my $ldc_subtype = $entry->get("ldcsubtype");
  my $ldc_role = $entry->get("ldcrole");
  my $nist_type = $entry->get("nisttype");
  my $nist_subtype = $entry->get("nistsubtype");
  my $nist_role = $entry->get("nistrole");
  
  $event_relation_type_mapping{"$ldc_type.$ldc_subtype"} = "$nist_type.$nist_subtype";
  
  my $ldc_fqrolename = "$ldc_type.$ldc_subtype\_$ldc_role";
  my $nist_fqrolename = "$nist_type.$nist_subtype\_$nist_role";
  $role_mapping{$ldc_fqrolename} = $nist_fqrolename;
}

# Load type mappings

my (%entity_type_mapping);
$filename = "data/nist-type-mapping-20180618.txt";
$filehandler = FileHandler->new($filename);
$header = $filehandler->get("HEADER");
$entries = $filehandler->get("ENTRIES");
$i=0;
foreach my $entry( $entries->toarray() ){
  $i++;
  #print "ENTRY # $i:\n", $entry->tostring(), "\n";
  my $ldc_type = $entry->get("LDCTypeOutput");
  my $nist_type = $entry->get("AIDAType");
  
  $entity_type_mapping{$ldc_type} = $nist_type;  
}
#####################################################################################
# Print document and document-element mapping in RDF Turtle format
#####################################################################################

open(OUTPUT, ">output/document-mapping.ttl");

foreach my $document($documents->toarray()) {
	my $document_id = $document->get("DOCUMENTID");
	my $node_id = "$document_id";
	print OUTPUT "\n# Document $document_id and its elements\n";
	print OUTPUT "ldc:$node_id rdf:type ldc:document ;\n";
  print OUTPUT "              rdf:ID \"$document_id\" ;\n";
  my @document_element_ids = map {"              ldc:has_element ldc:".$_}
                              map {$_->get("DOCUMENTELEMENTID")} 
                               $document->get("DOCUMENTELEMENTS")->toarray();
                               
  my $document_elements_rdf = join(" ;\n", @document_element_ids);
  print OUTPUT "$document_elements_rdf .\n";
}

foreach my $document_element($documentelements->toarray()) {
  my $document_element_id = $document_element->get("DOCUMENTELEMENTID");
  my $document_element_modality = $document_element->get("TYPE");
  my $document_id = $document_element->get("DOCUMENTID");
  my $node_id = "$document_element_id";
  print OUTPUT "\n# Document element $document_element_id and its parent\n";
  print OUTPUT "ldc:$node_id rdf:type ldc:document_element ;\n";
  print OUTPUT "              rdf:ID \"$document_element_id\" ;\n";
  print OUTPUT "              ldc:is_element_of ldc:$document_id ;\n";                               
  print OUTPUT "              ldc:modality ldc:$document_element_modality .\n";
}

close(OUTPUT);

open(OUTPUT, ">output/$TOPIC.all.ttl");

my $output_header = "
\@prefix ldcOnt: <http://darpa.mil/ontologies/SeedlingOntology/> .
\@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
\@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
\@prefix ldc:   <http://darpa.mil/annotations/ldc/> .
\@prefix aidaCommon: <http://darpa.mil/ontologies/AidaDomainOntologiesCommon#> .
\@prefix aif:   <http://www.isi.edu/aida/interchangeOntology#> .
";

print OUTPUT "$output_header\n";

#####################################################################################
# Process T101_ent_mentions.tab
#####################################################################################

$filename = "$annotations_dir/data/$TOPIC/$TOPIC\_ent_mentions.tab";
$filehandler = FileHandler->new($filename);
$header = $filehandler->get("HEADER");
$entries = $filehandler->get("ENTRIES"); 

# variable to hold entities
my $entities = Entities->new();
$i=0;
foreach my $entry( $entries->toarray() ){
	$i++;
	#print "ENTRY # $i:\n", $entry->tostring(), "\n";
	my $document_eid = $entry->get("provenance");
	my $thedocumentelement = $documentelements->get("BY_KEY", $document_eid);
	my $thedocumentelementmodality = $thedocumentelement->get("TYPE");
	my $document_id = $thedocumentelement->get("DOCUMENTID");
	my $mention = Mention->new();
	my $span = Span->new(
	             $entry->get("provenance"),
	             $document_eid,
	             $entry->get("textoffset_startchar"),
	             $entry->get("textoffset_endchar"),
	         );
	my $justification = Justification->new();
	$justification->add_span($span);
	$mention->add_justification($justification);
	$mention->set("MODALITY", $thedocumentelementmodality);
	$mention->set("MENTIONID", $entry->get("entitymention_id"));
	$mention->set("ENTITYID", $entry->get("entity_id"));
	$mention->set("TEXT_STRING", $entry->get("text_string"));
	$mention->set("JUSTIFICATION_STRING", $entry->get("justification"));
	$mention->set("TREEID", $entry->get("tree_id"));
	$mention->set("TYPE", $entry->get("type"));
	
	my $entity = $entities->get("BY_KEY", $entry->get("kb_id"));
	
	$entity->set("KBID", $entry->get("kb_id")) unless $entity->set("KBID");
	$entity->set("TYPE", $entry->get("type")) unless $entity->set("TYPE");
	$entity->add_mention($mention);
	
	$mappings{$mention->get("MENTIONID")} = {
		MENTIONID => $mention->get("MENTIONID"),
    ENTITYID => $mention->get("ENTITYID"),
		KBID => $entity->get("KBID"),
		TYPE => $mention->get("TYPE"),
		SOURCEDOCID => $document_id,
		SOURCEDOCEID => $document_eid,
	};
	$mappings{$mention->get("ENTITYID")} = {
    MENTIONID => $mention->get("MENTIONID"),
    ENTITYID => $mention->get("ENTITYID"),
		KBID => $entity->get("KBID"),
		TYPE => $mention->get("TYPE"),
    SOURCEDOCID => $document_id,
    SOURCEDOCEID => $document_eid,
	};
}

my $all_entities = $entities;

#####################################################################################
# Print entity mentions from T101_ent_mentions.tab in RDF Turtle format
#####################################################################################

foreach my $entity($entities->toarray()) {
  #&Super::dump_structure($entity, 'Entity');
  #print "Total mentions: ", scalar $entity->get("MENTIONS")->toarray(), "\n";

  my $node_id = $entity->get("KBID");
  my $entity_type = $entity->get("TYPE");
  
  print OUTPUT "\n\nldc:$node_id a aif:Entity ;\n";
  print OUTPUT "  aif:system ldc:LDCModelGenerator .\n";
  
  foreach my $entity_mention($entity->get("MENTIONS")->toarray()) {
  	my $entity_mention_id = $entity_mention->get("MENTIONID");
  	my $entity_mention_type = $entity_mention->get("TYPE");
    	my ($justification_source) = $entity_mention->get("SOURCE_DOCUMENT_ELEMENTS");
  	my $justification_type = $entity_mention->get("MODALITY");
    	my $text_string = $entity_mention->get("TEXT_STRING");
	$text_string =~ s/"/\\"/g;
  	if($justification_type eq "nil") {
     	print "--skipping over $entity_mention_id due to unknown modality\n";
      	next;
  }
  	die("Unknown Justification Type: $justification_type") 
      	if !(  
             $justification_type eq "txt" || 
             $justification_type eq "vid" ||
             $justification_type eq "img" ||
             $justification_type eq "psm" ||
             $justification_type eq "ltf"
          );
    $justification_type = "aif:TextJustification" 
      if($justification_type eq "txt" || $justification_type eq "psm" || $justification_type eq "ltf");
    $justification_type = "aif:ShotVideoJustification" if($justification_type eq "vid");
    $justification_type = "aif:ImageJustification" if($justification_type eq "img");
  	
	# FIXME: Usage a package for mapping instead of a pure lookup
  	my $type = $entity_mention_type;
	my $nist_type = $entity_type_mapping{$type};
	next unless $nist_type;
	
  	die "Undefined \$justification_type" unless $justification_type;
  	print OUTPUT "\n\n[ a                rdf:Statement ;\n";
    print OUTPUT "  rdf:object       ldcOnt:$nist_type ;\n";
    print OUTPUT "  rdf:predicate    rdf:type ;\n";
    print OUTPUT "  rdf:subject      ldc:$node_id ;\n";
    print OUTPUT "  aif:confidence   [ a                        aif:Confidence ;\n";
    print OUTPUT "                     aif:confidenceValue      \"1.0\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
    print OUTPUT "                     aif:system               ldc:LDCModelGenerator ;\n";
    print OUTPUT "                   ] ;\n";
    print OUTPUT "  aif:justifiedBy  [ a                        $justification_type ;\n";
    print OUTPUT "                     aif:confidence           [ a                       aif:Confidence ;\n";
    print OUTPUT "                                                aif:confidenceValue    \"1.0\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
    print OUTPUT "                                                aif:system              ldc:LDCModelGenerator ;\n";
    print OUTPUT "                                              ] ;\n";
    print OUTPUT "                     aif:ID                   ldc:$entity_mention_id ;\n";
#    print OUTPUT "                     aif:textString           \"$text_string\" ;\n";
    print OUTPUT "                     aif:source               \"$justification_source\" ;\n";
    
    if($justification_type eq "aif:TextJustification") {
    	my ($start) = $entity_mention->get("START");
    	my ($end) = $entity_mention->get("END");
    	
      $start = "1.0" if ($start eq "nil");
      $end = "1.0" if ($end eq "nil");
    	
    	print OUTPUT "                     aif:startOffset          \"$start\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
    	print OUTPUT "                     aif:endOffsetInclusive   \"$end\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
    }
    
    print OUTPUT "                     aif:system               ldc:LDCModelGenerator ;\n";
    print OUTPUT "                  ] ;\n";
    print OUTPUT "] .\n"; 
  }
}



#####################################################################################
# Process T101_evt_mentions.tab
#####################################################################################

$filename = "$annotations_dir/data/$TOPIC/$TOPIC\_evt_mentions.tab";
$filehandler = FileHandler->new($filename);
$header = $filehandler->get("HEADER");
$entries = $filehandler->get("ENTRIES"); 

# variable to hold entities
$entities = Entities->new();
$i=0;
foreach my $entry( $entries->toarray() ){
  $i++;
  #print "ENTRY # $i:\n", $entry->tostring(), "\n";
  my $document_eid = $entry->get("provenance");
  my $thedocumentelement = $documentelements->get("BY_KEY", $document_eid);
  my $thedocumentelementmodality = $thedocumentelement->get("TYPE");
  my $document_id = $thedocumentelement->get("DOCUMENTID");
  my $mention = Mention->new();
  my $span = Span->new(
               $entry->get("provenance"),
               $document_eid,
               $entry->get("textoffset_startchar"),
               $entry->get("textoffset_endchar"),
           );
  my $justification = Justification->new();
  $justification->add_span($span);
  $mention->add_justification($justification);
  $mention->set("MODALITY", $thedocumentelementmodality);
  $mention->set("MENTIONID", $entry->get("eventmention_id"));
  $mention->set("EVENTID", $entry->get("event_id"));
  $mention->set("TEXT_STRING", $entry->get("text_string"));
  $mention->set("JUSTIFICATION_STRING", $entry->get("justification"));
  $mention->set("TREEID", $entry->get("tree_id"));
  $mention->set("TYPE", $entry->get("type"));
  $mention->set("SUBTYPE", $entry->get("subtype"));
  
  my $entity = $entities->get("BY_KEY", $entry->get("kb_id"));
  
  $entity->set("KBID", $entry->get("kb_id")) unless $entity->set("KBID");
  $entity->set("TYPE", $entry->get("type")) unless $entity->set("TYPE");
  $entity->add_mention($mention);
  
  $mappings{$mention->get("MENTIONID")} = {
    MENTIONID => $mention->get("MENTIONID"),
    ENTITYID => $mention->get("ENTITYID"),
		KBID => $entity->get("KBID"),
		TYPE => $mention->get("TYPE").".".$mention->get("SUBTYPE"),
    SOURCEDOCID => $document_id,
    SOURCEDOCEID => $document_eid,
	};
  $mappings{$mention->get("EVENTID")} = {
    MENTIONID => $mention->get("MENTIONID"),
    ENTITYID => $mention->get("ENTITYID"),
		KBID => $entity->get("KBID"),
		TYPE => $mention->get("TYPE").".".$mention->get("SUBTYPE"),
    SOURCEDOCID => $document_id,
    SOURCEDOCEID => $document_eid,
	};
}

my $all_events = $entities;

#####################################################################################
# Print entity mentions from T101_evt_mentions.tab in RDF Turtle format
#####################################################################################

foreach my $entity($entities->toarray()) {
  #&Super::dump_structure($entity, 'Entity');
  #print "Total mentions: ", scalar $entity->get("MENTIONS")->toarray(), "\n";

  my $node_id = $entity->get("KBID");
  my $entity_type = $entity->get("TYPE");
  
  print OUTPUT "\n\nldc:$node_id a aif:Event ;\n";
  print OUTPUT "  aif:system ldc:LDCModelGenerator .\n";
  
  foreach my $entity_mention($entity->get("MENTIONS")->toarray()) {
    my $entity_mention_id = $entity_mention->get("MENTIONID");
    my $entity_mention_type = $entity_mention->get("TYPE").".".$entity_mention->get("SUBTYPE");
    my ($justification_source) = $entity_mention->get("SOURCE_DOCUMENT_ELEMENTS");
    my $justification_type = $entity_mention->get("MODALITY");
    my $text_string = $entity_mention->get("TEXT_STRING");
    $text_string =~ s/"/\\"/g;
    if($justification_type eq "nil") {
    	print "--skipping over $entity_mention_id due to unknown modality\n";
    	next;
    }
    
    die("Unknown Justification Type: $justification_type") 
      if !(  
             $justification_type eq "txt" || 
             $justification_type eq "vid" ||
             $justification_type eq "img" ||
             $justification_type eq "psm" ||
             $justification_type eq "ltf"
          );
    $justification_type = "aif:TextJustification" 
      if($justification_type eq "txt" || $justification_type eq "psm" || $justification_type eq "ltf");
    $justification_type = "aif:ShotVideoJustification" if($justification_type eq "vid");
    $justification_type = "aif:ImageJustification" if($justification_type eq "img");
    
    my $type = $entity_mention_type;
    my $nist_type = $event_relation_type_mapping{$type};
    next unless $nist_type;

    die "Undefined \$justification_type" unless $justification_type;
    print OUTPUT "\n\n[ a                rdf:Statement ;\n";
    print OUTPUT "  rdf:object       ldcOnt:$nist_type ;\n";
    print OUTPUT "  rdf:predicate    rdf:type ;\n";
    print OUTPUT "  rdf:subject      ldc:$node_id ;\n";
    print OUTPUT "  aif:confidence   [ a                        aif:Confidence ;\n";
    print OUTPUT "                     aif:confidenceValue      \"1.0\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
    print OUTPUT "                     aif:system               ldc:LDCModelGenerator ;\n";
    print OUTPUT "                   ] ;\n";
    print OUTPUT "  aif:justifiedBy  [ a                        $justification_type ;\n";
    print OUTPUT "                     aif:confidence           [ a                       aif:Confidence ;\n";
    print OUTPUT "                                                aif:confidenceValue    \"1.0\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
    print OUTPUT "                                                aif:system              ldc:LDCModelGenerator ;\n";
    print OUTPUT "                                              ] ;\n";
    print OUTPUT "                     aif:ID                   ldc:$entity_mention_id ;\n";
#    print OUTPUT "                     aif:textString           \"$text_string\" ;\n";
    print OUTPUT "                     aif:source               \"$justification_source\" ;\n";
    
    if($justification_type eq "aif:TextJustification") {
      my ($start) = $entity_mention->get("START");
      my ($end) = $entity_mention->get("END");
      
      $start = "1.0" if ($start eq "nil");
      $end = "1.0" if ($end eq "nil");
      
      print OUTPUT "                     aif:startOffset          \"$start\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
      print OUTPUT "                     aif:endOffsetInclusive   \"$end\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
    }
    
    print OUTPUT "                     aif:system               ldc:LDCModelGenerator ;\n";
    print OUTPUT "                  ] ;\n";
    print OUTPUT "] .\n"; 
  }
}

#####################################################################################
# Process T101_rel_mentions.tab
#####################################################################################

$filename = "$annotations_dir/data/$TOPIC/$TOPIC\_rel_mentions.tab";
$filehandler = FileHandler->new($filename);
$header = $filehandler->get("HEADER");
$entries = $filehandler->get("ENTRIES"); 

# variable to hold entities
$entities = Entities->new();
$i=0;
foreach my $entry( $entries->toarray() ){
  $i++;
  #print "ENTRY # $i:\n", $entry->tostring(), "\n";
  my $document_eid = $entry->get("provenance");
  my $thedocumentelement = $documentelements->get("BY_KEY", $document_eid);
  my $thedocumentelementmodality = $thedocumentelement->get("TYPE");
  my $document_id = $thedocumentelement->get("DOCUMENTID");
  my $mention = Mention->new();
  my $span = Span->new(
               $entry->get("provenance"),
               $document_eid,
               $entry->get("textoffset_startchar"),
               $entry->get("textoffset_endchar"),
           );
  my $justification = Justification->new();
  $justification->add_span($span);
  $mention->add_justification($justification);
  $mention->set("MODALITY", $thedocumentelementmodality);
  $mention->set("MENTIONID", $entry->get("relationmention_id"));
  $mention->set("RELATIONID", $entry->get("relation_id"));
  $mention->set("TEXT_STRING", $entry->get("text_string"));
  $mention->set("JUSTIFICATION_STRING", $entry->get("justification"));
  $mention->set("TREEID", $entry->get("tree_id"));
  $mention->set("TYPE", $entry->get("type"));
  $mention->set("SUBTYPE", $entry->get("subtype"));
  
  my $entity = $entities->get("BY_KEY", $entry->get("kb_id"));
  
  $entity->set("KBID", $entry->get("kb_id")) unless $entity->set("KBID");
  $entity->set("TYPE", $entry->get("type")) unless $entity->set("TYPE");
  $entity->add_mention($mention);
  
  $mappings{$mention->get("MENTIONID")} = {
    MENTIONID => $mention->get("MENTIONID"),
    ENTITYID => $mention->get("ENTITYID"),
		KBID => $entity->get("KBID"),
		TYPE => $mention->get("TYPE").".".$mention->get("SUBTYPE"),
    SOURCEDOCID => $document_id,
    SOURCEDOCEID => $document_eid,
	};
  $mappings{$mention->get("RELATIONID")} = {
    MENTIONID => $mention->get("MENTIONID"),
    ENTITYID => $mention->get("ENTITYID"),
		KBID => $entity->get("KBID"),
		TYPE => $mention->get("TYPE").".".$mention->get("SUBTYPE"),
    SOURCEDOCID => $document_id,
    SOURCEDOCEID => $document_eid,
	};
}

my $all_relations = $entities;

#####################################################################################
# Print entity mentions from T101_rel_mentions.tab in RDF Turtle format
#####################################################################################

foreach my $entity($entities->toarray()) {
  #&Super::dump_structure($entity, 'Entity');
  #print "Total mentions: ", scalar $entity->get("MENTIONS")->toarray(), "\n";

  my $node_id = $entity->get("KBID");
  my $entity_type = $entity->get("TYPE");
  
  print OUTPUT "\n\nldc:$node_id a aif:Relation ;\n";
  print OUTPUT "  aif:system ldc:LDCModelGenerator .\n";
  
  foreach my $entity_mention($entity->get("MENTIONS")->toarray()) {
    my $entity_mention_id = $entity_mention->get("MENTIONID");
    my $entity_mention_type = $entity_mention->get("TYPE").".".$entity_mention->get("SUBTYPE");
    my ($justification_source) = $entity_mention->get("SOURCE_DOCUMENT_ELEMENTS");
    my $justification_type = $entity_mention->get("MODALITY");
    my $text_string = $entity_mention->get("TEXT_STRING");
    $text_string =~ s/"/\\"/g;
    if($justification_type eq "nil") {
      print "--skipping over $entity_mention_id due to unknown modality\n";
      next;
    }
    
    die("Unknown Justification Type: $justification_type") 
      if !(  
             $justification_type eq "txt" || 
             $justification_type eq "vid" ||
             $justification_type eq "img" ||
             $justification_type eq "psm" ||
             $justification_type eq "ltf"
          );
    $justification_type = "aif:TextJustification" 
      if($justification_type eq "txt" || $justification_type eq "psm" || $justification_type eq "ltf");
    $justification_type = "aif:ShotVideoJustification" if($justification_type eq "vid");
    $justification_type = "aif:ImageJustification" if($justification_type eq "img");
    
    my $type = $entity_mention_type;
    my $nist_type = $event_relation_type_mapping{$type};
    next unless $nist_type;

    die "Undefined \$justification_type" unless $justification_type;
    print OUTPUT "\n\n[ a                rdf:Statement ;\n";
    print OUTPUT "  rdf:object       ldcOnt:$nist_type ;\n";
    print OUTPUT "  rdf:predicate    rdf:type ;\n";
    print OUTPUT "  rdf:subject      ldc:$node_id ;\n";
    print OUTPUT "  aif:confidence   [ a                        aif:Confidence ;\n";
    print OUTPUT "                     aif:confidenceValue      \"1.0\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
    print OUTPUT "                     aif:system               ldc:LDCModelGenerator ;\n";
    print OUTPUT "                   ] ;\n";
    print OUTPUT "  aif:justifiedBy  [ a                        $justification_type ;\n";
    print OUTPUT "                     aif:confidence           [ a                       aif:Confidence ;\n";
    print OUTPUT "                                                aif:confidenceValue    \"1.0\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
    print OUTPUT "                                                aif:system              ldc:LDCModelGenerator ;\n";
    print OUTPUT "                                              ] ;\n";
    print OUTPUT "                     aif:ID                   ldc:$entity_mention_id ;\n";
#    print OUTPUT "                     aif:textString           \"$text_string\" ;\n";
    print OUTPUT "                     aif:source               \"$justification_source\" ;\n";
    
    if($justification_type eq "aif:TextJustification") {
      my ($start) = $entity_mention->get("START");
      my ($end) = $entity_mention->get("END");
      
      $start = "1.0" if ($start eq "nil");
      $end = "1.0" if ($end eq "nil");
      
      print OUTPUT "                     aif:startOffset          \"$start\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
      print OUTPUT "                     aif:endOffsetInclusive   \"$end\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
    }
    
    print OUTPUT "                     aif:system               ldc:LDCModelGenerator ;\n";
    print OUTPUT "                  ] ;\n";
    print OUTPUT "] .\n"; 
  }
}

#####################################################################################
# Process T101_rel_slots.tab and print in turle-RDF format
#####################################################################################

$filename = "$annotations_dir/data/$TOPIC/$TOPIC\_rel_slots.tab";
$filehandler = FileHandler->new($filename);
$header = $filehandler->get("HEADER");
$entries = $filehandler->get("ENTRIES"); 

# variable to hold entities
$entities = Entities->new();
$i=0;
foreach my $entry( $entries->toarray() ){
  $i++;
  #print "ENTRY # $i:\n", $entry->tostring(), "\n";
  my $relationmention_id = $entry->get("relationmention_id");
  my $relationmention_doceid = "nil";
  $relationmention_doceid = $mappings{$relationmention_id}{SOURCEDOCEID}
     if $mappings{$relationmention_id}{SOURCEDOCEID};
  
  my $relation_type = $mappings{$relationmention_id}{TYPE}; 
  my $slot_type = $entry->get("slot_type");
  my $ldc_slot_name =  "$relation_type\_$slot_type";
  my $nist_slot_type = $role_mapping{$ldc_slot_name};  

  my $argument_id = $entry->get("arg_id");
  my $argumentmention_id = $mappings{$argument_id}{MENTIONID};
  my $argumentmention_doceid = "nil";
  $argumentmention_doceid = $mappings{$argument_id}{SOURCEDOCEID} 
    if $mappings{$argument_id}{SOURCEDOCEID};
  
  next if ($relationmention_doceid eq "nil" || $argumentmention_doceid eq "nil");    

  if($argumentmention_doceid ne $relationmention_doceid) {
    # Match if the docmentID is the same
    if($mappings{$relationmention_id}{SOURCEDOCID} ne $mappings{$argument_id}{SOURCEDOCID}) {
      print "Justification spans across multiple documents:\n", $entry->tostring(), "\n";
      next;
    }
  }
  
  my @justification_sources = keys {map {$_=>1} 
                                ($argumentmention_doceid, $relationmention_doceid)};
  
  unless(@justification_sources) {
  	print "No justification found:\n", $entry->tostring(), "\n";
  	next;
  }
      
  next unless $nist_slot_type;

  print OUTPUT "\n\n[ a                rdf:Statement ;\n";
  print OUTPUT "  rdf:object       ldc:$argumentmention_id ;\n";
  print OUTPUT "  rdf:predicate    ldcOnt:$nist_slot_type ;\n";
  print OUTPUT "  rdf:subject      ldc:$relationmention_id ;\n";
  print OUTPUT "  aif:confidence   [ a                        aif:Confidence ;\n";
  print OUTPUT "                     aif:confidenceValue      \"1.0\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
  print OUTPUT "                     aif:system               ldc:LDCModelGenerator ;\n";
  print OUTPUT "                   ] ;\n";
  
  
  foreach my $justification_source(@justification_sources) {
	  my $thedocumentelement = $documentelements->get("BY_KEY", $justification_source);
	  my $justification_type = $thedocumentelement->get("TYPE");
	  if($justification_type eq "nil") {
	    print "--skipping over $relationmention_id due to unknown modality\n";
	    next;
	  }
	    
	  die("Unknown Justification Type: $justification_type\n for: ", $entry->tostring(), "\n") 
	    if !(  
	           $justification_type eq "txt" || 
	           $justification_type eq "vid" ||
	           $justification_type eq "img" ||
             $justification_type eq "psm" ||
             $justification_type eq "ltf"
          );
    $justification_type = "aif:TextJustification" 
      if($justification_type eq "txt" || $justification_type eq "psm" || $justification_type eq "ltf");
	  $justification_type = "aif:ShotVideoJustification" if($justification_type eq "vid");
	  $justification_type = "aif:ImageJustification" if($justification_type eq "img");
	  
	  print OUTPUT "  aif:justifiedBy  [ a                        $justification_type ;\n";
	  print OUTPUT "                     aif:confidence           [ a                       aif:Confidence ;\n";
	  print OUTPUT "                                                aif:confidenceValue    \"1.0\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
	  print OUTPUT "                                                aif:system              ldc:LDCModelGenerator ;\n";
	  print OUTPUT "                                              ] ;\n";
	  print OUTPUT "                     aif:source               \"$justification_source\" ;\n";
	  print OUTPUT "                  ] ;\n";
  }

  print OUTPUT "  aif:system       ldc:LDCModelGenerator ;\n";
  print OUTPUT "] .\n"; 

}

#####################################################################################
# Process T101_evt_slots.tab and print in turle-RDF format
#####################################################################################

$filename = "$annotations_dir/data/$TOPIC/$TOPIC\_evt_slots.tab";
$filehandler = FileHandler->new($filename);
$header = $filehandler->get("HEADER");
$entries = $filehandler->get("ENTRIES"); 

# variable to hold entities
$entities = Entities->new();
$i=0;
foreach my $entry( $entries->toarray() ){
  $i++;
  #print "ENTRY # $i:\n", $entry->tostring(), "\n";
  my $eventmention_id = $entry->get("eventmention_id");
  my $eventmention_doceid = "nil";
  $eventmention_doceid = $mappings{$eventmention_id}{SOURCEDOCEID}
     if $mappings{$eventmention_id}{SOURCEDOCEID};
  
  my $event_type = $mappings{$eventmention_id}{TYPE}; 
  my $slot_type = $entry->get("slot_type");
  my $ldc_slot_name =  "$event_type\_$slot_type";
  my $nist_slot_type = $role_mapping{$ldc_slot_name};  

  my $argument_id = $entry->get("arg_id");
  my $argumentmention_id = $mappings{$argument_id}{MENTIONID};
  my $argumentmention_doceid = "nil";
  $argumentmention_doceid = $mappings{$argument_id}{SOURCEDOCEID} 
    if $mappings{$argument_id}{SOURCEDOCEID};

  next if ($eventmention_doceid eq "nil" || $argumentmention_doceid eq "nil");
  
  if($argumentmention_doceid ne $eventmention_doceid) {
  	# Match if the docmentID is the same
  	if($mappings{$eventmention_id}{SOURCEDOCID} ne $mappings{$argument_id}{SOURCEDOCID}) {
  		print "Justification spans across multiple documents:\n", $entry->tostring(), "\n";
  		next;
  	}
  }
  
  my @justification_sources = keys {map {$_=>1} 
                                ($argumentmention_doceid, $eventmention_doceid)};
                                
  unless(@justification_sources) {
    print "No justification found:\n", $entry->tostring(), "\n";
    next;
  }
  
  next unless $nist_slot_type;

  print OUTPUT "\n\n[ a                rdf:Statement ;\n";
  print OUTPUT "  rdf:object       ldc:$argumentmention_id ;\n";
  print OUTPUT "  rdf:predicate    ldcOnt:$nist_slot_type ;\n";
  print OUTPUT "  rdf:subject      ldc:$eventmention_id ;\n";
  print OUTPUT "  aif:confidence   [ a                        aif:Confidence ;\n";
  print OUTPUT "                     aif:confidenceValue      \"1.0\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
  print OUTPUT "                     aif:system               ldc:LDCModelGenerator ;\n";
  print OUTPUT "                   ] ;\n";
  
  foreach my $justification_source(@justification_sources) {
	  my $thedocumentelement = $documentelements->get("BY_KEY", $justification_source);
	  my $justification_type = $thedocumentelement->get("TYPE");  
	  if($justification_type eq "nil") {
	    print "--skipping over $eventmention_id due to unknown modality\n";
	    next;
	  }
	    
	  die("Unknown Justification Type: $justification_type\n for: ", $entry->tostring(), "\n") 
	    if !(  
	           $justification_type eq "txt" || 
	           $justification_type eq "vid" ||
	           $justification_type eq "img" ||
             $justification_type eq "psm" ||
             $justification_type eq "ltf"
          );
    $justification_type = "aif:TextJustification" 
      if($justification_type eq "txt" || $justification_type eq "psm" || $justification_type eq "ltf");
	  $justification_type = "aif:ShotVideoJustification" if($justification_type eq "vid");
	  $justification_type = "aif:ImageJustification" if($justification_type eq "img");
	  
	  print OUTPUT "  aif:justifiedBy  [ a                        $justification_type ;\n";
	  print OUTPUT "                     aif:confidence           [ a                       aif:Confidence ;\n";
	  print OUTPUT "                                                aif:confidenceValue    \"1.0\"^^<http://www.w3.org/2001/XMLSchema#double> ;\n";
	  print OUTPUT "                                                aif:system              ldc:LDCModelGenerator ;\n";
	  print OUTPUT "                                              ] ;\n";
	  print OUTPUT "                     aif:source               \"$justification_source\" ;\n";
	  print OUTPUT "                  ] ;\n";
  }
  
  print OUTPUT "  aif:system       ldc:LDCModelGenerator ;\n";
  print OUTPUT "] .\n"; 

}
close(OUTPUT);


