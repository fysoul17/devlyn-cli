# Replica read contract

An aggregate read examines every configured replica until a record is found. If none can supply a record, `ReplicaUnavailable` outranks `CorruptReplica`, which outranks `RecordMissing`, regardless of the order in which those failures were observed.

A valid record from any replica wins over failures from earlier replicas.
