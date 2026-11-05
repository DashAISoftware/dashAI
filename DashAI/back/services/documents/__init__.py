"""Create folders and their Data documents in one transaction.

The upload flow first creates one ``NOT_STARTED`` row per file and then queues
a ``DocumentJob`` for each one. A folder upload must not leave a folder behind
without its documents, so this service validates every name before writing and
stores the folder and the rows in a single transaction.
"""
