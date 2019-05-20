# Confidence aggregation docker for task1 class responses

(Last modified: May 20, 2019)

This document describes how to use the docker to aggregate confidences of task1 class query responses. The layout of this document is as following:

  1. How to build the docker
  2. How to run the docker
  3. How is aggregate confidence computed
  4. Revision history

# How to build the docker

In order to build the docker, assuming that you are inside the following directory:

`dockers/TA1_CL_ConfidenceAggregation`

Once you are inside the above mentioned directory, you would need to run the following command:

~~~
make build
~~~

# How to run the docker

In order to run the docker, first you would need to change the value of the following variables inside the Makefile:

~~~
HOST_INPUT_DIR
HOST_OUTPUT_DIR
~~~

Once the above change has been made, run the following command to run the docker over the `HOST_INPUT_DIR`

~~~
make run
~~~

Make sure that the value of `HOST_INPUT_DIR` is the absolute path of the directory containing the SPARQL output of a task1 run as produced by `NIST SPARQL query application docker for M18`.

Alternatively, you may run the docker as:

~~~
make run HOST_INPUT_DIR=/absolute/path/to/inputdir HOST_OUTPUT_DIR=/absolute/path/to/outputdir
~~~

# How is aggregate confidence computed

The output of running task1 class queries over a task1-run using `SPARQL query application docker for M18` is a set of files that contains one response per line. Each response contains tab separated values corresponding to the following fields (in that order):

| Column  | Description
---|---------|-------------
1. |   ?docid       |  sourceDocument
2. |   ?query_type  |  query type
3. |   ?cluster     |  ?cluster containing ?member1 of type ?type that matches ?query_type
4. |   ?type        |  matching ?type
5. |   ?infj_span   |  informativeJustification span
6. |   ?t_cv        |  confidenceValue of asserting ?member being of ?type
7. |   ?cm_cv       |  confidenceValue of asserting ?member being a member of the ?cluster
8. |   ?j_cv        |  confidenceValue of informativeJustification

The default aggregate confidence of a ?cluster is computed as the product of the following columns:

| Column  | Description
---|---------|-------------
1. |   ?t_cv        |  confidenceValue of asserting ?member being of ?type
2. |   ?cm_cv       |  confidenceValue of asserting ?member being a member of the ?cluster
3. |   ?j_cv        |  confidenceValue of informativeJustification

# Revision history:
### May 20, 2019
  * Initial version